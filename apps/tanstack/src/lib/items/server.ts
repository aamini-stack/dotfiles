import { redirect } from '@tanstack/react-router'
import { createServerFn } from '@tanstack/react-start'
import { z } from 'zod'

import { getCurrentSession } from '@/lib/auth/session'

import {
	createItemForUser,
	deleteItemForUser,
	listItemsForUser,
} from './repository'

async function requireUserId() {
	const session = await getCurrentSession()
	if (!session) throw redirect({ href: '/auth/login' })
	return session.user.id
}

export const listItems = createServerFn({ method: 'GET' }).handler(async () =>
	listItemsForUser(await requireUserId()),
)

export const createItem = createServerFn({ method: 'POST' })
	.validator(z.object({ name: z.string().trim().min(1).max(120) }))
	.handler(async ({ data }) =>
		createItemForUser(await requireUserId(), data.name),
	)

export const deleteItem = createServerFn({ method: 'POST' })
	.validator(z.object({ id: z.string().min(1) }))
	.handler(async ({ data }) =>
		deleteItemForUser(await requireUserId(), data.id),
	)
