import { $ } from "bun"
import { copyFile, readdir, stat } from "node:fs/promises"
import { join, relative } from "node:path"

export interface Pair {
  name: string
  expected: string
  actual: string
  diff?: string
}

export type Mode = "actual" | "wipe" | "diff"

export const MODES: Mode[] = ["actual", "wipe", "diff"]

async function walk(dir: string, out: string[] = []): Promise<string[]> {
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const p = join(dir, entry.name)
    if (entry.isDirectory()) {
      if (entry.name === "node_modules" || entry.name.startsWith(".")) continue
      await walk(p, out)
    } else if (entry.name.endsWith("-actual.png")) {
      out.push(p)
    }
  }
  return out
}

export async function findPairs(target: string): Promise<Pair[]> {
  const info = await stat(target)
  if (!info.isDirectory()) {
    throw new Error(`not a directory: ${target}`)
  }
  const actuals = await walk(target)
  const pairs: Pair[] = []
  for (const actual of actuals.sort()) {
    const expected = actual.replace(/-actual\.png$/, "-expected.png")
    const diff = actual.replace(/-actual\.png$/, "-diff.png")
    const pair: Pair = {
      name: relative(target, actual).replace(/-actual\.png$/, ""),
      expected,
      actual,
    }
    try {
      await stat(expected)
    } catch {
      continue
    }
    try {
      await stat(diff)
      pair.diff = diff
    } catch {}
    pairs.push(pair)
  }
  return pairs
}

export function explicitPair(expected: string, actual: string): Pair {
  return { name: actual, expected, actual }
}

export async function approve(pair: Pair): Promise<void> {
  await copyFile(pair.actual, pair.expected)
}

export interface Raster {
  rgba: Buffer
  w: number
  h: number
}

async function rgbaOf(png: string): Promise<Buffer> {
  return Buffer.from(await $`magick ${png} -depth 8 rgba:-`.arrayBuffer())
}

export async function rasterTo(file: string, w: number, h: number, out: string): Promise<Raster> {
  await $`magick ${file} -resize ${`${w}x${h}`} -background black -gravity center -extent ${`${w}x${h}`} ${out}`.quiet()
  return { rgba: await rgbaOf(out), w, h }
}

export async function diffRaster(pair: Pair, w: number, h: number, out: string): Promise<Raster> {
  if (pair.diff) {
    return rasterTo(pair.diff, w, h, out)
  }
  await $`magick compare -metric AE -highlight-color "#ff3b30" -lowlight-color none ${pair.expected} ${pair.actual} ${out}`.nothrow().quiet()
  return rasterTo(out, w, h, out)
}

export function wipe(e: Raster, a: Raster, cutFrac: number): Buffer {
  const { w, h } = e
  const cut = Math.max(0, Math.min(w, Math.round(w * cutFrac)))
  const out = Buffer.allocUnsafe(e.rgba.length)
  const rowBytes = w * 4
  for (let y = 0; y < h; y++) {
    const off = y * rowBytes
    e.rgba.copy(out, off, off, off + cut * 4)
    a.rgba.copy(out, off + cut * 4, off + cut * 4, off + rowBytes)
  }
  for (let y = 0; y < h; y++) {
    for (let d = 0; d < 2 && cut + d < w; d++) {
      const p = y * rowBytes + (cut + d) * 4
      out[p] = 255
      out[p + 1] = 180
      out[p + 2] = 40
      out[p + 3] = 255
    }
  }
  return out
}
