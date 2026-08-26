import { $ } from "bun"
import { rm } from "node:fs/promises"
import type { Pair } from "./images.ts"

const IMAGE_EXT = /\.(png|jpe?g|webp|gif|bmp|tiff?|avif)$/i

async function extract(rev: string, file: string, out: string): Promise<boolean> {
  const result = await $`jj file show -r ${rev} -- ${file}`.nothrow().quiet()
  if (result.exitCode !== 0 || result.stdout.length === 0) return false
  await Bun.write(out, result.stdout)
  return true
}

async function blankFrom(src: string, out: string): Promise<void> {
  await $`magick ${src + "[0]"} -alpha off -fill white -colorize 100 ${out}`.quiet()
}

async function makePair(rev: string, file: string, stem: string, tmp: string): Promise<Pair | null> {
  const ext = file.slice(file.lastIndexOf(".") + 1)
  const rawBefore = `${tmp}/${stem}.before.${ext}`
  const rawAfter = `${tmp}/${stem}.after.${ext}`
  const [haveBefore, haveAfter] = await Promise.all([
    extract(`${rev}@-`, file, rawBefore),
    extract(rev, file, rawAfter),
  ])
  if (!haveBefore && !haveAfter) {
    console.error(`pix jj: ${file} not found at ${rev} or its parent`)
    return null
  }
  if (!haveBefore) await blankFrom(rawAfter, rawBefore)
  if (!haveAfter) await blankFrom(rawBefore, rawAfter)
  const expected = `${tmp}/${stem}-expected.png`
  const actual = `${tmp}/${stem}-actual.png`
  await $`magick ${rawBefore + "[0]"} ${expected}`.quiet()
  await $`magick ${rawAfter + "[0]"} ${actual}`.quiet()
  await rm(rawBefore, { force: true })
  await rm(rawAfter, { force: true })
  return { name: stem, expected, actual }
}

export async function jjPairs(rev: string, onlyFile: string | null, tmp: string): Promise<Pair[]> {
  if (onlyFile) {
    const pair = await makePair(rev, onlyFile, "pair", tmp)
    if (!pair) throw new Error(`${onlyFile} not found at ${rev} or its parent`)
    return [pair]
  }
  const diff = await $`jj diff -r ${rev} --name-only`.text()
  const files = diff.split("\n").filter((f) => IMAGE_EXT.test(f))
  if (files.length === 0) throw new Error(`no image changes in ${rev}`)
  const pairs: Pair[] = []
  for (const [i, file] of files.entries()) {
    const stem = `${String(i + 1).padStart(3, "0")}_${file.replace(/\.[^.]+$/, "").replaceAll("/", "__")}`
    const pair = await makePair(rev, file, stem, tmp)
    if (pair) pairs.push(pair)
  }
  if (pairs.length === 0) throw new Error(`no image changes in ${rev}`)
  return pairs
}
