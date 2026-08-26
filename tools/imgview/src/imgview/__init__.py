"""Display an image inline via the Kitty graphics protocol.

Multiplexers (herdr, tmux) report PTY sizes in cells but no pixel geometry, so
tools that size output from cell pixel size (chafa --fit-width) collapse to
~1px/cell. We instead query the terminal for cell pixels (CSI 16 t) and tell
the terminal exactly how many cells the image should occupy, letting it scale.
"""

import argparse
import base64
import fcntl
import os
import re
import select
import struct
import subprocess
import sys
import tempfile
import termios
import tty

CHUNK = 4096
FALLBACK_CELL_W = 10
FALLBACK_CELL_H = 20


def tty_cells(fd):
    rows, cols, _, _ = struct.unpack(
        "HHHH", fcntl.ioctl(fd, termios.TIOCGWINSZ, b"\0" * 8)
    )
    return rows, cols


def cell_pixels(fd):
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        os.write(fd, b"\x1b[16t")
        ready, _, _ = select.select([fd], [], [], 0.3)
        data = os.read(fd, 64) if ready else b""
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    m = re.search(rb"\x1b\[6;(\d+);(\d+)t", data)
    if not m:
        return FALLBACK_CELL_W, FALLBACK_CELL_H
    return int(m.group(2)), int(m.group(1))


def image_pixels(path):
    out = subprocess.run(
        ["magick", "identify", "-format", "%w %h", path],
        check=True,
        capture_output=True,
        text=True,
    )
    w, h = out.stdout.split()
    return int(w), int(h)


def to_png(path, target_width):
    if target_width <= 0:
        target_width = 1
    out = subprocess.run(
        ["magick", path + "[0]", "-resize", f"{target_width}x>", "png:-"],
        check=True,
        capture_output=True,
    )
    return out.stdout


def transmit(out, png, cols, rows):
    payload = base64.b64encode(png)
    pos = 0
    first = True
    while pos < len(payload) or first:
        chunk = payload[pos : pos + CHUNK]
        pos += CHUNK
        more = 1 if pos < len(payload) else 0
        if first:
            ctrl = f"a=T,f=100,c={cols},r={rows},m={more}"
            first = False
        else:
            ctrl = f"m={more}"
        out.write(f"\x1b_G{ctrl};".encode() + chunk + b"\x1b\\")
    out.flush()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("file", help="image path, or - for stdin")
    p.add_argument(
        "--hold",
        action="store_true",
        help="wait for a keypress, then delete the image (for TUI suspend)",
    )
    p.add_argument("--cols", type=int, default=0, help="override width in cells")
    args = p.parse_args()

    tmp = None
    if args.file == "-":
        with tempfile.NamedTemporaryFile(suffix=".img", delete=False) as tmp:
            tmp.write(sys.stdin.buffer.read())
            src = tmp.name
    else:
        src = args.file

    try:
        tty_fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY)
    except OSError:
        tty_fd = None

    try:
        if tty_fd is not None:
            tty_rows, tty_cols = tty_cells(tty_fd)
            cell_w, cell_h = cell_pixels(tty_fd)
        else:
            tty_rows, tty_cols = 24, 80
            cell_w, cell_h = FALLBACK_CELL_W, FALLBACK_CELL_H

        img_w, img_h = image_pixels(src)

        cols = args.cols or tty_cols
        max_rows = max(tty_rows - (1 if args.hold else 0), 1)
        rows = max(1, round(img_h * cols * cell_w / (img_w * cell_h)))
        if rows > max_rows:
            rows = max_rows
            cols = max(1, round(img_w * rows * cell_h / (img_h * cell_w)))

        png = to_png(src, cols * cell_w * 2)
        transmit(sys.stdout.buffer, png, cols, rows)
        sys.stdout.write("\n" * rows)
        sys.stdout.flush()

        if args.hold and tty_fd is not None:
            sys.stdout.write("[image — press any key]")
            sys.stdout.flush()
            old = termios.tcgetattr(tty_fd)
            try:
                tty.setraw(tty_fd)
                os.read(tty_fd, 1)
            finally:
                termios.tcsetattr(tty_fd, termios.TCSADRAIN, old)
            sys.stdout.write("\x1b_Ga=d,d=A\x1b\\\r\x1b[2K\n")
            sys.stdout.flush()
    finally:
        if tty_fd is not None:
            os.close(tty_fd)
        if tmp is not None:
            os.unlink(tmp.name)


if __name__ == "__main__":
    main()
