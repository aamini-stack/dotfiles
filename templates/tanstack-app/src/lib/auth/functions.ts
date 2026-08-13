import { redirect } from '@tanstack/react-router'

import { getCurrentSession } from './session'

export async function redirectAuthenticatedUsers() {
	const session = await getCurrentSession()

	if (session) {
		throw redirect({ to: '/' })
	}
}

export async function redirectUnauthenticatedUsers({
	redirectTo,
}: {
	redirectTo: string
}) {
	const session = await getCurrentSession()

	if (!session) {
		throw redirect({
			href: `/auth/login?redirect=${encodeURIComponent(redirectTo)}`,
		})
	}

	return session
}
