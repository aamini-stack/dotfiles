import { afterEach, describe, expect, test, vi } from 'vite-plus/test'

import { createPostHogProxyRequestHandler } from './proxy'

const handler = createPostHogProxyRequestHandler({
	publicPathPrefix: '/api/ingest',
	upstreamOrigin: 'https://us.i.posthog.com',
})

afterEach(() => {
	vi.unstubAllGlobals()
})

function stubFetch() {
	const fetchMock = vi.fn(
		async (_input: RequestInfo | URL, _init?: RequestInit) =>
			new Response('ok'),
	)
	vi.stubGlobal('fetch', fetchMock)
	return fetchMock
}

describe('createPostHogProxyRequestHandler', () => {
	test('forwards the trimmed path and query upstream', async () => {
		const fetchMock = stubFetch()

		await handler(
			new Request('http://localhost/api/ingest/decide/?v=3', {
				method: 'POST',
				body: '{}',
			}),
		)

		const url = fetchMock.mock.calls[0]?.[0]
		if (!(url instanceof URL)) throw new Error('expected a URL')
		expect(url.toString()).toBe('https://us.i.posthog.com/decide/?v=3')
	})

	test('strips hop-by-hop headers', async () => {
		const fetchMock = stubFetch()

		await handler(
			new Request('http://localhost/api/ingest/e', {
				headers: { connection: 'keep-alive', 'keep-alive': 'timeout=5' },
			}),
		)

		const init = fetchMock.mock.calls[0]?.[1]
		const headers = new Headers(init?.headers)
		expect(headers.has('connection')).toBe(false)
		expect(headers.has('keep-alive')).toBe(false)
		expect(headers.has('host')).toBe(false)
	})
})
