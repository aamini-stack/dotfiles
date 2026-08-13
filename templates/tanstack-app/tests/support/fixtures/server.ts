import { setupServer } from 'msw/node'
import type { SetupServer } from 'msw/node'

import { createMswFixture } from './msw-fixture'

export type MswServerFixture = {
	msw: SetupServer
}

export const test = createMswFixture<SetupServer>({
	createContext: async () => {
		const { default: handlers } = await import('@tests/support/mocks/handlers')
		return setupServer(...handlers)
	},
	lifecycle: {
		start: (server) => {
			server.listen({ onUnhandledRequest: 'bypass' })
		},
		stop: (server) => {
			server.close()
		},
		reset: (server) => {
			server.resetHandlers()
		},
	},
})

export { afterEach, beforeEach, describe, expect, vi } from 'vite-plus/test'
