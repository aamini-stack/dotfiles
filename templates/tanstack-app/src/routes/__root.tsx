import { QueryClientProvider } from '@tanstack/react-query'
import {
	HeadContent,
	Outlet,
	Scripts,
	createRootRoute,
} from '@tanstack/react-router'
import posthog from 'posthog-js'
import { useEffect } from 'react'

import { queryClient } from '@/lib/utils/query'

import appCss from '../styles.css?url'

export const Route = createRootRoute({
	head: () => ({
		meta: [
			{ charSet: 'utf-8' },
			{ name: 'viewport', content: 'width=device-width, initial-scale=1' },
			{ title: '__APP_NAME__' },
		],
		links: [{ rel: 'stylesheet', href: appCss }],
	}),
	component: () => (
		<>
			<html lang="en">
				<head>
					<HeadContent />
				</head>
				<body>
					<QueryClientProvider client={queryClient}>
						<PostHog />
						<Outlet />
					</QueryClientProvider>
					<Scripts />
				</body>
			</html>
		</>
	),
})

function PostHog() {
	useEffect(() => {
		const key = import.meta.env.VITE_PUBLIC_POSTHOG_KEY
		if (key) posthog.init(key, { api_host: '/api/ingest' })
	}, [])
	return null
}
