import { test as baseTest } from 'vite-plus/test'

export interface MswLifecycle<TContext> {
	start: (context: TContext) => Promise<void> | void
	stop: (context: TContext) => Promise<void> | void
	reset: (context: TContext) => Promise<void> | void
}

export interface CreateMswFixtureOptions<TContext> {
	createContext: () => Promise<TContext> | TContext
	lifecycle: MswLifecycle<TContext>
}

export interface MswFixture<TContext> {
	msw: TContext
	_cleanup: void
}

export function createMswFixture<TContext>({
	createContext,
	lifecycle,
}: CreateMswFixtureOptions<TContext>) {
	let context: TContext | undefined

	async function ensureContext(): Promise<TContext> {
		if (!context) {
			context = await createContext()
		}
		return context
	}

	return baseTest.extend<MswFixture<TContext>>({
		msw: [
			async ({}, use: (value: TContext) => Promise<void>) => {
				const ctx = await ensureContext()
				await lifecycle.start(ctx)
				await use(ctx)
				await lifecycle.stop(ctx)
			},
			{ auto: true, scope: 'worker' },
		],
		_cleanup: [
			async ({ msw }, use) => {
				await use()
				await lifecycle.reset(msw)
			},
			{ auto: true },
		],
	})
}

export { afterEach, beforeEach, describe, expect, vi } from 'vite-plus/test'
