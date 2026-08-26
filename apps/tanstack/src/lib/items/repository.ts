import { and, eq } from 'drizzle-orm'

import { db } from '@/db/connection'
import { items } from '@/db/schema'

export async function listItemsForUser(
	userId: string,
	database: typeof db = db,
) {
	return database.select().from(items).where(eq(items.userId, userId))
}

export async function createItemForUser(
	userId: string,
	name: string,
	database: typeof db = db,
) {
	const [item] = await database
		.insert(items)
		.values({ id: crypto.randomUUID(), name, userId, createdAt: new Date() })
		.returning()
	return item
}

export async function deleteItemForUser(
	userId: string,
	id: string,
	database: typeof db = db,
) {
	await database
		.delete(items)
		.where(and(eq(items.id, id), eq(items.userId, userId)))
}
