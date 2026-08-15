import { PostHogProvider } from '@posthog/react'
import type { PropsWithChildren } from 'react'

const options = {
	api_host: import.meta.env.VITE_POSTHOG_HOST,
	ui_host: 'https://us.posthog.com',
	defaults: '2026-05-30',
	person_profiles: 'always',
	capture_exceptions: true,
} as const

export function PostHogInit({ children }: PropsWithChildren) {
	return (
		<PostHogProvider
			apiKey={import.meta.env.VITE_POSTHOG_PROJECT_TOKEN}
			options={options}
		>
			{children}
		</PostHogProvider>
	)
}
