import type { ExtensionAPI } from '@earendil-works/pi-coding-agent'
import { Markdown, Text, truncateToWidth } from '@earendil-works/pi-tui'

// Highlights CSS colors in pi's rendered chat with a matching preview color.
// Supported forms: #rgb/#rgba/#rrggbb/#rrggbbaa, rgb()/rgba(), and oklch().
// Alpha is preserved in labels but ignored for terminal swatches.
const COLOR_RE =
	/#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})\b|\b(?:rgba?|oklch)\([^)]*\)/gi
const PATCHED = Symbol.for('pi-extension.color-values.patched')

const RESET_FG_BG = '\x1b[39;49m'
const ANSI_RE = /\x1b\[[0-9;]*[A-Za-z]|\x1b\][^\x07]*(?:\x07|\x1b\\)/g

type Rgb = { r: number; g: number; b: number; alpha?: number }
type Oklch = { l: number; c: number; h: number; alpha?: number }

type RenderableClass = {
	prototype: {
		render: (width: number) => string[]
		[PATCHED]?: true
	}
}

function clamp(value: number, min = 0, max = 1): number {
	return Math.min(max, Math.max(min, value))
}

function srgbToLinear(value: number): number {
	const c = value / 255
	return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
}

function linearToSrgb(value: number): number {
	const c = clamp(value)
	const encoded = c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055
	return Math.round(clamp(encoded) * 255)
}

function rgbToOklch({ r, g, b, alpha }: Rgb): Oklch {
	const lr = srgbToLinear(r)
	const lg = srgbToLinear(g)
	const lb = srgbToLinear(b)

	const l = Math.cbrt(0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb)
	const m = Math.cbrt(0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb)
	const s = Math.cbrt(0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb)

	const okL = 0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s
	const okA = 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s
	const okB = 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s

	const c = Math.hypot(okA, okB)
	const h = c < 0.00001 ? 0 : (Math.atan2(okB, okA) * 180) / Math.PI
	return { l: okL, c, h: h < 0 ? h + 360 : h, alpha }
}

function oklchToRgb({ l, c, h, alpha }: Oklch): Rgb {
	const hue = (h * Math.PI) / 180
	const a = c * Math.cos(hue)
	const b = c * Math.sin(hue)

	const lPrime = l + 0.3963377774 * a + 0.2158037573 * b
	const mPrime = l - 0.1055613458 * a - 0.0638541728 * b
	const sPrime = l - 0.0894841775 * a - 1.291485548 * b

	const l3 = lPrime ** 3
	const m3 = mPrime ** 3
	const s3 = sPrime ** 3

	return {
		r: linearToSrgb(4.0767416621 * l3 - 3.3077115913 * m3 + 0.2309699292 * s3),
		g: linearToSrgb(-1.2684380046 * l3 + 2.6097574011 * m3 - 0.3413193965 * s3),
		b: linearToSrgb(-0.0041960863 * l3 - 0.7034186147 * m3 + 1.707614701 * s3),
		alpha,
	}
}

function parseHex(token: string): Rgb | undefined {
	const hex = token.slice(1)
	if (hex.length === 3 || hex.length === 4) {
		return {
			r: Number.parseInt(hex[0]! + hex[0]!, 16),
			g: Number.parseInt(hex[1]! + hex[1]!, 16),
			b: Number.parseInt(hex[2]! + hex[2]!, 16),
			alpha: hex.length === 4 ? Number.parseInt(hex[3]! + hex[3]!, 16) / 255 : undefined,
		}
	}
	if (hex.length === 6 || hex.length === 8) {
		return {
			r: Number.parseInt(hex.slice(0, 2), 16),
			g: Number.parseInt(hex.slice(2, 4), 16),
			b: Number.parseInt(hex.slice(4, 6), 16),
			alpha: hex.length === 8 ? Number.parseInt(hex.slice(6, 8), 16) / 255 : undefined,
		}
	}
	return undefined
}

function parseAlpha(value: string | undefined): number | undefined {
	if (!value) return undefined
	const trimmed = value.trim()
	if (trimmed.endsWith('%')) return clamp(Number.parseFloat(trimmed) / 100)
	const parsed = Number.parseFloat(trimmed)
	return Number.isFinite(parsed) ? clamp(parsed) : undefined
}

function parseRgbChannel(value: string): number | undefined {
	const trimmed = value.trim()
	const parsed = Number.parseFloat(trimmed)
	if (!Number.isFinite(parsed)) return undefined
	return Math.round(clamp(trimmed.endsWith('%') ? (parsed / 100) * 255 : parsed, 0, 255))
}

function parseRgb(token: string): Rgb | undefined {
	const body = token.slice(token.indexOf('(') + 1, -1).trim()
	const [channelsPart, slashAlpha] = body.split('/')
	const parts = channelsPart!.includes(',')
		? channelsPart!.split(',').map((part) => part.trim())
		: channelsPart!.trim().split(/\s+/)
	if (parts.length < 3) return undefined
	const [r, g, b] = parts.slice(0, 3).map(parseRgbChannel)
	if (r === undefined || g === undefined || b === undefined) return undefined
	const alpha = parseAlpha(slashAlpha ?? (parts.length > 3 ? parts[3] : undefined))
	return { r, g, b, alpha }
}

function parseOklch(token: string): Oklch | undefined {
	const body = token.slice(token.indexOf('(') + 1, -1).trim()
	const [valuesPart, slashAlpha] = body.split('/')
	const parts = valuesPart!.trim().split(/\s+/)
	if (parts.length < 3) return undefined

	const lRaw = parts[0]!
	const cRaw = parts[1]!
	const hRaw = parts[2]!.replace(/deg$/i, '')
	const l = Number.parseFloat(lRaw)
	const c = Number.parseFloat(cRaw)
	const h = Number.parseFloat(hRaw)
	if (!Number.isFinite(l) || !Number.isFinite(c) || !Number.isFinite(h)) return undefined

	return {
		l: lRaw.endsWith('%') ? l / 100 : l,
		c,
		h: ((h % 360) + 360) % 360,
		alpha: parseAlpha(slashAlpha),
	}
}

function parseColor(token: string): { rgb: Rgb; oklch: Oklch; source: 'rgb' | 'oklch' | 'hex' } | undefined {
	if (token.startsWith('#')) {
		const rgb = parseHex(token)
		return rgb ? { rgb, oklch: rgbToOklch(rgb), source: 'hex' } : undefined
	}
	if (/^rgba?\(/i.test(token)) {
		const rgb = parseRgb(token)
		return rgb ? { rgb, oklch: rgbToOklch(rgb), source: 'rgb' } : undefined
	}
	if (/^oklch\(/i.test(token)) {
		const oklch = parseOklch(token)
		return oklch ? { rgb: oklchToRgb(oklch), oklch, source: 'oklch' } : undefined
	}
	return undefined
}

function formatAlpha(alpha: number | undefined): string {
	return alpha === undefined || alpha >= 1 ? '' : ` / ${Number(alpha.toFixed(3))}`
}

function formatRgb({ r, g, b, alpha }: Rgb): string {
	return `rgb(${r} ${g} ${b}${formatAlpha(alpha)})`
}

function formatOklch({ l, c, h, alpha }: Oklch): string {
	return `oklch(${l.toFixed(4)} ${c.toFixed(4)} ${h.toFixed(1)}${formatAlpha(alpha)})`
}

function readableTextColor({ r, g, b }: Rgb): '0;0;0' | '255;255;255' {
	const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
	return luminance > 0.55 ? '0;0;0' : '255;255;255'
}

function paintColor(token: string): string {
	const color = parseColor(token)
	if (!color) return token

	const { rgb } = color
	const fg = readableTextColor(rgb)
	return `\x1b[38;2;${fg}m\x1b[48;2;${rgb.r};${rgb.g};${rgb.b}m ${token} ${RESET_FG_BG}`
}

function trimTrailingPadding(line: string): string {
	// Pi renderers often return lines already padded to the terminal width, with
	// reset escape sequences after the padding. If we append color conversions to
	// those padded lines, they exceed the terminal width and Pi aborts rendering.
	const ansiSuffixMatch = line.match(/((?:\x1b\[[0-9;]*[A-Za-z]|\x1b\][^\x07]*(?:\x07|\x1b\\))*)$/)
	const suffix = ansiSuffixMatch?.[0] ?? ''
	const body = suffix ? line.slice(0, -suffix.length) : line
	return body.replace(/[ \t]+$/, '') + suffix
}

function stripAnsiWithMap(line: string): { visible: string; rawAtVisible: number[] } {
	let visible = ''
	const rawAtVisible: number[] = []
	let rawIndex = 0

	for (const match of line.matchAll(ANSI_RE)) {
		const start = match.index ?? 0
		for (; rawIndex < start; rawIndex++) {
			visible += line[rawIndex]!
			rawAtVisible.push(rawIndex)
		}
		rawIndex = start + match[0].length
	}

	for (; rawIndex < line.length; rawIndex++) {
		visible += line[rawIndex]!
		rawAtVisible.push(rawIndex)
	}

	return { visible, rawAtVisible }
}

function colorizeLine(line: string, width: number): string {
	if (width <= 0) return line

	const trimmed = trimTrailingPadding(line)
	const { visible, rawAtVisible } = stripAnsiWithMap(trimmed)
	COLOR_RE.lastIndex = 0

	let colorized = ''
	let lastRawIndex = 0
	let found = false

	for (const match of visible.matchAll(COLOR_RE)) {
		const visibleStart = match.index ?? 0
		const visibleEnd = visibleStart + match[0].length
		const rawStart = rawAtVisible[visibleStart]
		const rawEnd = rawAtVisible[visibleEnd] ?? trimmed.length
		if (rawStart === undefined) continue

		found = true
		colorized += trimmed.slice(lastRawIndex, rawStart)
		colorized += paintColor(match[0])
		lastRawIndex = rawEnd
	}

	if (!found) colorized = trimmed
	else colorized += trimmed.slice(lastRawIndex)

	// Last line of defense: every custom-rendered line must be <= render(width).
	return truncateToWidth(colorized, width, '')
}

function patchRender(cls: RenderableClass) {
	const proto = cls.prototype
	if (proto[PATCHED]) return

	const originalRender = proto.render
	proto.render = function patchedRender(width: number): string[] {
		return originalRender.call(this, width).map((line) => colorizeLine(line, width))
	}
	proto[PATCHED] = true
}

export default function (_pi: ExtensionAPI) {
	patchRender(Markdown as unknown as RenderableClass)
	patchRender(Text as unknown as RenderableClass)
}
