import { createFileRoute } from '@tanstack/react-router'

import { getAuth } from '@/lib/auth/config'

// Reverse proxies (pitchfork) rewrite Host to the upstream and carry the
// public origin in x-forwarded-*. better-auth's oAuthProxy skip-check reads
// the raw request URL, so without this rewrite it thinks it's already on the
// production origin and sends Google the unregistered proxy callback URL.
function withForwardedOrigin(request: Request) {
	const host = request.headers.get('x-forwarded-host')
	if (!host) return request
	const proto = request.headers.get('x-forwarded-proto') ?? 'https'
	const url = new URL(request.url)
	return new Request(`${proto}://${host}${url.pathname}${url.search}`, request)
}

export const Route = createFileRoute('/api/auth/$')({
	server: {
		handlers: {
			GET: async ({ request }: { request: Request }) => {
				return await getAuth().handler!(withForwardedOrigin(request))
			},
			POST: async ({ request }: { request: Request }) => {
				return await getAuth().handler!(withForwardedOrigin(request))
			},
		},
	},
})
