import type { ExtensionAPI } from '@mariozechner/pi-coding-agent'
import { Markdown, Text } from '@mariozechner/pi-tui'

// Matches CSS-style hex colors: #rgb, #rgba, #rrggbb, #rrggbbaa.
// For alpha forms, alpha is ignored for terminal rendering.
const HEX_COLOR_RE =
	/#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})\b/g
const PATCHED = Symbol.for('pi-extension.hex-color-history.patched')

type RenderableClass = {
	prototype: {
		render: (width: number) => string[]
		[PATCHED]?: true
	}
}

function parseHexColor(token: string): [number, number, number] | undefined {
	const hex = token.slice(1)

	if (hex.length === 3 || hex.length === 4) {
		return [
			Number.parseInt(hex[0]! + hex[0]!, 16),
			Number.parseInt(hex[1]! + hex[1]!, 16),
			Number.parseInt(hex[2]! + hex[2]!, 16),
		]
	}

	if (hex.length === 6 || hex.length === 8) {
		return [
			Number.parseInt(hex.slice(0, 2), 16),
			Number.parseInt(hex.slice(2, 4), 16),
			Number.parseInt(hex.slice(4, 6), 16),
		]
	}

	return undefined
}

function readableTextColor([r, g, b]: [number, number, number]):
	| '0;0;0'
	| '255;255;255' {
	const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
	return luminance > 0.55 ? '0;0;0' : '255;255;255'
}

function paintHexColor(token: string): string {
	const rgb = parseHexColor(token)
	if (!rgb) return token

	const [r, g, b] = rgb
	const fg = readableTextColor(rgb)

	// Truecolor foreground/background. No visible-width change, so wrapping/layout
	// in the already-rendered chat history stays correct.
	return `\x1b[38;2;${fg}m\x1b[48;2;${r};${g};${b}m${token}\x1b[39;49m`
}

function colorizeHexCodes(line: string): string {
	return line.replace(HEX_COLOR_RE, paintHexColor)
}

function patchRender(cls: RenderableClass) {
	const proto = cls.prototype
	if (proto[PATCHED]) return

	const originalRender = proto.render
	proto.render = function patchedRender(width: number): string[] {
		return originalRender.call(this, width).map(colorizeHexCodes)
	}
	proto[PATCHED] = true
}

export default function () {
	// Chat history for normal user/assistant messages is rendered through Markdown.
	// Some built-in history/status entries use Text, so patch that too.
	patchRender(Markdown as unknown as RenderableClass)
	patchRender(Text as unknown as RenderableClass)
}
