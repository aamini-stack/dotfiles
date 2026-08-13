import { setupWorker } from 'msw/browser'
import type { SetupWorker } from 'msw/browser'

import { createMswFixture } from './msw-fixture'

export type MswBrowserFixture = {
	msw: SetupWorker
}

export const test = createMswFixture<SetupWorker>({
	createContext: async () => {
		const { default: handlers } = await import('@tests/support/mocks/handlers')
		return setupWorker(...handlers)
	},
	lifecycle: {
		start: async (worker) => {
			await worker.start({ quiet: true, onUnhandledRequest: 'bypass' })
		},
		stop: (worker) => worker.stop(),
		reset: (worker) => worker.resetHandlers(),
	},
})

export { afterEach, beforeEach, describe, expect, vi } from 'vite-plus/test'
