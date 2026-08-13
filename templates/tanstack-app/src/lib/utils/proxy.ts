type PostHogProxyOptions = {
	publicPathPrefix: string
	upstreamOrigin: string
	upstreamPathPrefix?: string
}

const HOP_BY_HOP_HEADERS = new Set([
	'connection',
	'keep-alive',
	'proxy-authenticate',
	'proxy-authorization',
	'te',
	'trailer',
	'transfer-encoding',
	'upgrade',
])

export function createPostHogProxyRequestHandler(options: PostHogProxyOptions) {
	return async function proxyPostHogRequest(request: Request) {
		const requestUrl = new URL(request.url)
		const upstreamPath = requestUrl.pathname.startsWith(
			options.publicPathPrefix,
		)
			? requestUrl.pathname.slice(options.publicPathPrefix.length)
			: ''
		const upstreamUrl = new URL(
			buildUpstreamPath(options, upstreamPath) + requestUrl.search,
			trimTrailingSlash(options.upstreamOrigin) + '/',
		)
		const headers = new Headers(request.headers)
		const connectionHeader = headers.get('connection')

		for (const header of HOP_BY_HOP_HEADERS) {
			headers.delete(header)
		}

		if (connectionHeader) {
			for (const token of connectionHeader.split(',')) {
				const header = token.trim().toLowerCase()
				if (header) {
					headers.delete(header)
				}
			}
		}

		headers.delete('host')

		const requestInit: RequestInit = {
			method: request.method,
			headers,
			redirect: 'follow',
		}

		if (request.method !== 'GET' && request.method !== 'HEAD') {
			requestInit.body = await request.arrayBuffer()
		}

		const upstreamResponse = await fetch(upstreamUrl, requestInit)

		return new Response(upstreamResponse.body, {
			status: upstreamResponse.status,
			statusText: upstreamResponse.statusText,
			headers: upstreamResponse.headers,
		})
	}
}

function buildUpstreamPath(options: PostHogProxyOptions, upstreamPath: string) {
	const prefix = trimSlashes(options.upstreamPathPrefix ?? '')
	const path = trimLeadingSlash(upstreamPath)

	if (!prefix) {
		return path
	}

	if (!path) {
		return prefix
	}

	return `${prefix}/${path}`
}

function trimLeadingSlash(value: string) {
	return value.replace(/^\/+/, '')
}

function trimSlashes(value: string) {
	return value.replace(/^\/|\/$/g, '')
}

function trimTrailingSlash(value: string) {
	return value.replace(/\/$/, '')
}
