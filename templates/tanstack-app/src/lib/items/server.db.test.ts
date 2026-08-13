import {
	describe,
	expect,
	test,
	type Database,
} from '@tests/support/fixtures/db'

import { user } from '@/db/schema'

import {
	createItemForUser,
	deleteItemForUser,
	listItemsForUser,
} from './repository'

async function seedUser(db: Database) {
	const id = crypto.randomUUID()
	await db.insert(user).values({
		id,
		name: 'Test User',
		email: `${id}@example.com`,
		createdAt: new Date(),
		updatedAt: new Date(),
	})
	return id
}

describe('pantry items', () => {
	test('creates, lists, and deletes items scoped to the user', async ({
		db,
	}) => {
		const userId = await seedUser(db)

		const item = await createItemForUser(userId, 'Olive oil', db)
		expect(item?.name).toBe('Olive oil')

		const stocked = await listItemsForUser(userId, db)
		expect(stocked).toHaveLength(1)
		expect(stocked[0]?.id).toBe(item?.id)

		expect(await listItemsForUser('user-2', db)).toHaveLength(0)

		if (!item) throw new Error('expected created item')
		await deleteItemForUser(userId, item.id, db)
		expect(await listItemsForUser(userId, db)).toHaveLength(0)
	})

	test('does not delete items owned by another user', async ({ db }) => {
		const userId = await seedUser(db)

		const item = await createItemForUser(userId, 'Sea salt', db)
		if (!item) throw new Error('expected created item')
		await deleteItemForUser('user-2', item.id, db)

		expect(await listItemsForUser(userId, db)).toHaveLength(1)
	})
})
