import { expect } from 'vite-plus/test'
import { page } from 'vite-plus/test/browser'

const defaultViewport = { width: 1440, height: 900 }

let currentViewport = defaultViewport

export async function waitForImages(timeout = 1000) {
	await Promise.all(
		Array.from(document.images, (image) => {
			if (image.complete) return Promise.resolve()
			return Promise.race([
				image.decode().catch(() => undefined),
				new Promise<void>((resolve) => setTimeout(resolve, timeout)),
			])
		}),
	)
}

export async function waitForLayout() {
	await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()))
}

export function resetScreenshotHarness(viewport: {
	width: number
	height: number
}) {
	const frame = window.frameElement

	if (frame instanceof HTMLIFrameElement) {
		frame.style.width = `${viewport.width}px`
		frame.style.height = `${viewport.height}px`
	}
}

export async function setViewport(viewport = defaultViewport): Promise<void> {
	currentViewport = viewport
	await page.viewport(viewport.width, viewport.height)
	resetScreenshotHarness(viewport)
}

export interface ExpectScreenshotOptions {
	name: string
	viewport?: { width: number; height: number }
	prepare?: () => Promise<void> | void
	fullPage?: boolean
}

function clampBodyToViewport<T>(
	body: HTMLElement,
	viewport: { width: number; height: number },
	action: () => Promise<T>,
): Promise<T> {
	const originalHeight = body.style.height
	const originalOverflow = body.style.overflow
	const originalMinHeight = body.style.minHeight
	const originalPointerEvents = body.style.pointerEvents

	body.style.height = `${viewport.height}px`
	body.style.minHeight = `${viewport.height}px`
	body.style.overflow = 'hidden'
	body.style.pointerEvents = 'none'

	return action().finally(() => {
		body.style.height = originalHeight
		body.style.minHeight = originalMinHeight
		body.style.overflow = originalOverflow
		body.style.pointerEvents = originalPointerEvents
	})
}

export async function expectScreenshot(
	target: HTMLElement | SVGElement,
	options: ExpectScreenshotOptions,
) {
	await setViewport(options.viewport)
	await options.prepare?.()
	await expect.element(target).toBeVisible()
	await document.fonts.ready
	await waitForImages()
	await waitForLayout()

	const screenshotOptions = {
		animations: 'disabled' as const,
		scale: 'css' as const,
		caret: 'hide' as const,
	}

	const capture = () =>
		expect.element(target).toMatchScreenshot(`${options.name}.png`, {
			screenshotOptions,
			comparatorOptions: {
				allowedMismatchedPixelRatio: 0,
				allowedMismatchedPixels: 0,
			},
			timeout: 5000,
		})

	if (options.fullPage || target !== document.body) {
		await capture()
	} else {
		await clampBodyToViewport(document.body, currentViewport, capture)
	}
}
