import { vi } from 'vite-plus/test'

type MockSession = unknown

const authState = vi.hoisted<{ session: MockSession }>(() => ({
	session: null,
}))

export function setMockSession(session: MockSession) {
	authState.session = session
}

vi.mock('@/lib/auth/client', () => ({
	authClient: {
		useSession: () => ({ data: authState.session, isPending: false }),
		signIn: {
			email: vi.fn(),
			social: vi.fn(),
		},
		signUp: {
			email: vi.fn(async () => ({ error: null })),
		},
		requestPasswordReset: vi.fn(),
		resetPassword: vi.fn(),
		signOut: vi.fn(),
	},
}))

vi.mock('@/lib/auth/functions', () => ({
	getCurrentSession: () => authState.session,
	redirectAuthenticatedUsers: () => undefined,
	redirectUnauthenticatedUsers: () => ({ session: authState.session }),
}))

vi.mock('@/lib/auth/session', () => ({
	getCurrentSession: () => Promise.resolve(authState.session),
}))

vi.mock('@/routes/__root', async () => {
	const React = await import('react')
	const { Outlet, createRootRouteWithContext } =
		await import('@tanstack/react-router')

	return {
		Route: createRootRouteWithContext()({
			component: () => React.createElement(Outlet),
		}),
	}
})
