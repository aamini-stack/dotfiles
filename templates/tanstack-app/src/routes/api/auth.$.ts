import { createFileRoute } from '@tanstack/react-router'

import { allowedHosts, getAuth } from '@/lib/auth/config'

// Reverse proxies (pitchfork) rewrite Host to the upstream and carry the
// public origin in x-forwarded-*. better-auth's oAuthProxy skip-check reads
// the raw request URL, so without this rewrite it thinks it's already on the
// production origin and sends Google the unregistered proxy callback URL.
// The headers are client-controllable, so only rewrite when the host is in
// our allowlist and the proto is http/https — otherwise leave the request
// untouched and let better-auth fall back to the upstream origin.
function isAllowedHost(host: string) {
	return allowedHosts.some((pattern) => {
		const regex = new RegExp(
			`^${pattern.replace(/[.+?^${}()|[\]\\]/g, '\\$&').replaceAll('*', '[^/]*')}$`,
			'i',
		)
		return regex.test(host)
	})
}

function withForwardedOrigin(request: Request) {
	const host = request.headers.get('x-forwarded-host')
	const proto = request.headers.get('x-forwarded-proto') ?? 'https'
	if (
		!host ||
		!isAllowedHost(host) ||
		(proto !== 'http' && proto !== 'https')
	) {
		return request
	}
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
