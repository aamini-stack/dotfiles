const ESC = "\x1b"
const ST = `${ESC}\\`
const CHUNK = 4096

export function kittyGraphicsSupported(): boolean {
  if (process.env.HERDR_ENV === "1") return true
  if (process.env.KITTY_WINDOW_ID) return true
  if ((process.env.TERM ?? "").includes("kitty")) return true
  return ["ghostty", "WezTerm", "mintty", "rio"].includes(process.env.TERM_PROGRAM ?? "")
}

export function displayRgba(id: number, rgba: Buffer, w: number, h: number, cols: number, rows: number): string {
  const b64 = rgba.toString("base64")
  const parts: string[] = []
  let off = 0
  while (off < b64.length || off === 0) {
    const chunk = b64.slice(off, off + CHUNK)
    const last = off + CHUNK >= b64.length
    const ctrl =
      off === 0 ? `a=T,f=32,i=${id},s=${w},v=${h},c=${cols},r=${rows},q=2,m=${last ? 0 : 1}` : `m=${last ? 0 : 1}`
    parts.push(`${ESC}_G${ctrl};${chunk}${ST}`)
    off += CHUNK
    if (b64.length === 0) break
  }
  return parts.join("")
}

export function deleteImage(id: number): string {
  return `${ESC}_Ga=d,d=i,i=${id},q=2${ST}`
}
