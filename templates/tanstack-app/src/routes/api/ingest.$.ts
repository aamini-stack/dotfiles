import { createFileRoute } from '@tanstack/react-router'

import { serverEnv } from '@/env.server'
import { createPostHogProxyRequestHandler } from '@/lib/utils/proxy'

const proxyRequest = createPostHogProxyRequestHandler({
	publicPathPrefix: `${serverEnv.VITE_POSTHOG_HOST ?? '/api/ingest'}/`,
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
