#!/usr/bin/env bun
import { $ } from "bun"
import { BoxRenderable, createCliRenderer, TextRenderable, type CliRenderer } from "@opentui/core"
import { mkdtemp, rm } from "node:fs/promises"
import { tmpdir } from "node:os"
import { join } from "node:path"
import {
  approve,
  diffRaster,
  explicitPair,
  findPairs,
  rasterTo,
  wipe,
  MODES,
  type Mode,
  type Pair,
  type Raster,
} from "./images.ts"
import { jjPairs } from "./jj.ts"
import { deleteImage, displayRgba, kittyGraphicsSupported } from "./kitty.ts"

const CELL_ASPECT = Number(process.env.PIX_CELL_ASPECT ?? 0.5)
const PX_PER_CELL = Number(process.env.PIX_PX_PER_CELL ?? 16)
const EMIT_THROTTLE_MS = 66

type Status = "pending" | "approved" | "rejected"
type Blink = "actual" | "expected"

interface PairRasters {
  expected: Raster
  actual: Raster
  diff?: Raster
}

function usage(): never {
  console.error(`usage:
  pix                        scan the git worktree root (or cwd) for Playwright *-actual.png / *-expected.png pairs
  pix <dir>                  scan dir for Playwright pairs
  pix <expected> <actual>    diff a single pair
  pix jj <rev> [file]        diff image changes in a jj revision (or a single file at that revision)`)
  process.exit(2)
}

async function main() {
  const args = process.argv.slice(2)
  if (args.includes("--help") || args.includes("-h")) usage()

  const tmp = await mkdtemp(join(tmpdir(), "pix-"))

  let pairs: Pair[]
  let scanDir: string | null = null
  if (args[0] === "jj") {
    const rev = args[1]
    if (!rev || args.length > 3) usage()
    try {
      pairs = await jjPairs(rev, args[2] ?? null, tmp)
    } catch (err) {
      console.error(`pix jj: ${err instanceof Error ? err.message : err}`)
      process.exit(1)
    }
  } else if (args.length === 0) {
    const root = await $`git rev-parse --show-toplevel`.nothrow().text()
    scanDir = root.trim() || process.cwd()
    pairs = await findPairs(scanDir)
  } else if (args.length === 1) {
    scanDir = args[0]
    pairs = await findPairs(scanDir)
  } else if (args.length === 2) {
    pairs = [explicitPair(args[0], args[1])]
  } else {
    usage()
  }

  const kittyOk = kittyGraphicsSupported()
  const statuses = new Map<string, Status>()
  let idx = 0
  let mode: Mode = "actual"
  let cut = 0.5
  let blink: Blink = "actual"
  let nextImageId = 1
  let displayedId = 0
  let emittedKey = ""
  let lastEmitAt = 0
  let buildSeq = 0
  let rasters: PairRasters | null = null
  let rasterKey = ""

  const renderer: CliRenderer = await createCliRenderer({ exitOnCtrlC: true })

  const header = new TextRenderable(renderer, { id: "header", height: 1 })
  const listBox = new BoxRenderable(renderer, {
    id: "list",
    width: 34,
    borderStyle: "rounded",
    flexDirection: "column",
    overflow: "hidden",
  })
  const viewBox = new BoxRenderable(renderer, {
    id: "view",
    flexGrow: 1,
    borderStyle: "rounded",
    flexDirection: "column",
  })
  const imageArea = new BoxRenderable(renderer, { id: "img", flexGrow: 1 })
  const statusLine = new TextRenderable(renderer, { id: "status", height: 1, fg: "#888888" })
  const footer = new TextRenderable(renderer, {
    id: "footer",
    height: 1,
    fg: "#888888",
    content: "j/k pairs · h/l wipe · space blink · 1/2/3 mode · s list · a approve · r reject · q quit",
  })
  const mainRow = new BoxRenderable(renderer, { id: "main", flexGrow: 1, flexDirection: "row" })

  viewBox.add(imageArea)
  viewBox.add(statusLine)
  mainRow.add(listBox)
  mainRow.add(viewBox)
  renderer.root.add(header)
  renderer.root.add(mainRow)
  renderer.root.add(footer)

  function statusOf(p: Pair): Status {
    return statuses.get(p.actual) ?? "pending"
  }

  function renderList() {
    for (const child of listBox.getChildren()) child.destroy()
    pairs.forEach((p, i) => {
      const s = statusOf(p)
      const mark = s === "approved" ? "✓" : s === "rejected" ? "✗" : "•"
      const fg = i === idx ? "#7aa2f7" : s === "approved" ? "#9ece6a" : s === "rejected" ? "#f7768e" : "#aaaaaa"
      listBox.add(
        new TextRenderable(renderer, {
          id: `pair-${i}`,
          content: `${i === idx ? "▸" : " "} ${mark} ${p.name}`,
          fg,
          height: 1,
        }),
      )
    })
    const pending = pairs.filter((p) => statusOf(p) === "pending").length
    header.content = `pix · ${pairs.length} pairs (${pending} pending) · ${mode}`
  }

  function renderStatus() {
    if (pairs.length === 0) {
      statusLine.content = "no image pairs found"
      return
    }
    const pair = pairs[idx]
    const view =
      mode === "diff" ? "diff" : mode === "actual" ? blink : blink === "expected" ? "expected" : cut >= 1 ? "actual" : "wipe"
    statusLine.content = `${pair.name} · ${view}${mode === "wipe" && view === "wipe" ? ` ${Math.round(cut * 100)}%` : ""}`
  }

  function select(next: number) {
    if (pairs.length === 0) return
    const clamped = Math.max(0, Math.min(pairs.length - 1, next))
    if (clamped === idx) return
    idx = clamped
    cut = 0.5
    blink = "actual"
    renderList()
    renderStatus()
  }

  function setMode(next: Mode) {
    if (next === mode) return
    mode = next
    renderList()
    renderStatus()
  }

  renderer.keyInput.on("keypress", (key) => {
    if (key.name === "q" || (key.ctrl && key.name === "c")) {
      renderer.destroy()
      return
    }
    if (key.name === "j" || key.name === "down") select(idx + 1)
    else if (key.name === "k" || key.name === "up") select(idx - 1)
    else if (key.name === "h" || key.name === "left") {
      cut = Math.max(0, cut - (key.shift ? 0.1 : 0.02))
      blink = "actual"
      renderStatus()
    } else if (key.name === "l" || key.name === "right") {
      cut = Math.min(1, cut + (key.shift ? 0.1 : 0.02))
      blink = "actual"
      renderStatus()
    } else if (key.name === "space") {
      blink = blink === "actual" ? "expected" : "actual"
      renderStatus()
    } else if (key.name === "1") setMode("actual")
    else if (key.name === "2") setMode("wipe")
    else if (key.name === "3") setMode("diff")
    else if (key.name === "s") {
      listBox.visible = !listBox.visible
      renderStatus()
    }
    else if (key.name === "tab") setMode(MODES[(MODES.indexOf(mode) + 1) % MODES.length])
    else if (key.name === "a" && pairs.length > 0) {
      const pair = pairs[idx]
      statuses.set(pair.actual, "approved")
      void approve(pair)
      renderList()
      const nextPending = pairs.findIndex((p, i) => i > idx && statusOf(p) === "pending")
      if (nextPending >= 0) select(nextPending)
    } else if (key.name === "r" && pairs.length > 0) {
      statuses.set(pairs[idx].actual, "rejected")
      renderList()
    } else if (key.name === "u" && pairs.length > 0) {
      statuses.delete(pairs[idx].actual)
      renderList()
    } else if (key.name === "R" && scanDir) {
      void findPairs(scanDir).then((found) => {
        pairs = found
        idx = Math.min(idx, Math.max(0, pairs.length - 1))
        renderList()
        renderStatus()
      })
    }
  })

  function desiredKey(): string {
    if (pairs.length === 0 || imageArea.width < 4 || imageArea.height < 2) return ""
    const pair = pairs[idx]
    const view =
      mode === "diff" ? "diff" : mode === "actual" ? blink : blink === "expected" ? "expected" : cut >= 1 ? "actual" : "wipe"
    return [pair.actual, mode, view, view === "wipe" ? cut.toFixed(3) : "", imageArea.width, imageArea.height].join("::")
  }

  async function ensureRasters(pair: Pair, w: number, h: number): Promise<PairRasters> {
    const key = `${pair.actual}::${w}x${h}`
    if (rasters && rasterKey === key) return rasters
    const seq = ++buildSeq
    statusLine.content = `${pair.name} · rasterizing…`
    const [expected, actual] = await Promise.all([
      rasterTo(pair.expected, w, h, join(tmp, `e-${seq}.png`)),
      rasterTo(pair.actual, w, h, join(tmp, `a-${seq}.png`)),
    ])
    if (seq !== buildSeq) throw new Error("stale")
    rasters = { expected, actual }
    rasterKey = key
    return rasters
  }

  renderer.on("frame", () => {
    if (!kittyOk || renderer.isDestroyed) return
    const key = desiredKey()
    if (!key || key === emittedKey) return
    const now = Date.now()
    if (now - lastEmitAt < EMIT_THROTTLE_MS) {
      setTimeout(() => imageArea.requestRender(), EMIT_THROTTLE_MS)
      return
    }
    emittedKey = key
    lastEmitAt = now
    const pair = pairs[idx]
    const w = imageArea.width * PX_PER_CELL
    const h = Math.round(imageArea.height * (PX_PER_CELL / CELL_ASPECT))
    const modeSnap = mode
    const blinkSnap = blink
    const cutSnap = cut
    const col = imageArea.screenX + 1
    const row = imageArea.screenY + 1
    const cols = imageArea.width
    const rows = imageArea.height
    void (async () => {
      try {
        const r = await ensureRasters(pair, w, h)
        if (renderer.isDestroyed || key !== desiredKey()) return
        let raster: Raster
        if (modeSnap === "diff") {
          if (!r.diff) {
            const seq = ++buildSeq
            const d = await diffRaster(pair, w, h, join(tmp, `d-${seq}.png`))
            if (renderer.isDestroyed || key !== desiredKey()) return
            r.diff = d
          }
          raster = r.diff
        } else if (modeSnap === "actual") {
          raster = blinkSnap === "expected" ? r.expected : r.actual
        } else if (blinkSnap === "expected") {
          raster = r.expected
        } else if (cutSnap >= 1) {
          raster = r.actual
        } else {
          raster = { rgba: wipe(r.expected, r.actual, cutSnap), w: r.expected.w, h: r.expected.h }
        }
        const id = nextImageId++
        let out = ""
        if (displayedId !== 0) out += deleteImage(displayedId)
        out += `\x1b[${row};${col}H` + displayRgba(id, raster.rgba, raster.w, raster.h, cols, rows)
        process.stdout.write(out)
        displayedId = id
        renderStatus()
      } catch (err) {
        if (err instanceof Error && err.message === "stale") return
        statusLine.content = `render failed: ${err instanceof Error ? err.message : err}`
      }
    })()
  })

  renderer.on("destroy", () => {
    if (displayedId !== 0) process.stdout.write(deleteImage(displayedId))
    void rm(tmp, { recursive: true, force: true })
  })

  renderList()
  if (!kittyOk) {
    statusLine.content = "kitty graphics unavailable in this terminal (works in herdr, kitty, ghostty, wezterm)"
  } else {
    renderStatus()
  }
}

await main()
