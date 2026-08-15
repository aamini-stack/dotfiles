import { PostHog } from 'posthog-node'

import { serverEnv as env } from '@/env.server'

let posthogClient: PostHog | null = null

export function getPostHogClient() {
	if (!env.VITE_POSTHOG_PROJECT_TOKEN) return null

	if (!posthogClient) {
		posthogClient = new PostHog(env.VITE_POSTHOG_PROJECT_TOKEN, {
			host: 'https://us.i.posthog.com',
			flushAt: 1,
			flushInterval: 0,
		})
	}
	return posthogClient
}
