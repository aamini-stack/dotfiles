import { createFileRoute } from '@tanstack/react-router'

import { createPostHogProxyRequestHandler } from '@/lib/utils/proxy'

const proxyRequest = createPostHogProxyRequestHandler({
	publicPathPrefix: '/api/ingest/',
	upstreamOrigin: 'https://us.i.posthog.com',
})

export const Route = createFileRoute('/api/ingest/$')({
	server: {
		handlers: {
			GET: ({ request }) => proxyRequest(request),
			POST: ({ request }) => proxyRequest(request),
			OPTIONS: ({ request }) => proxyRequest(request),
		},
	},
})
