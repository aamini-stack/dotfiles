import { renderRoute } from '@tests/support/render/route'
import { beforeEach, describe, expect, test, vi } from 'vite-plus/test'

type PantryItem = { id: string; name: string; userId: string; createdAt: Date }

const itemsState = vi.hoisted((): { items: PantryItem[] } => ({
	items: [],
}))

vi.mock('@/lib/items/server', () => ({
	listItems: () => Promise.resolve(itemsState.items),
	createItem: async ({ data }: { data: { name: string } }) => {
		itemsState.items.push({
			id: crypto.randomUUID(),
			name: data.name,
			userId: 'user-1',
			createdAt: new Date(),
		})
	},
	deleteItem: async ({ data }: { data: { id: string } }) => {
		itemsState.items = itemsState.items.filter((item) => item.id !== data.id)
	},
}))

const testSession = {
	user: { id: 'user-1', name: 'Test User', email: 'test@example.com' },
	session: { id: 'session-1', token: 'token' },
}

describe('pantry route', () => {
	beforeEach(() => {
		itemsState.items = []
	})

	test('shows the empty state', async () => {
		const { screen } = await renderRoute({
			path: '/pantry',
			session: testSession,
		})

		await expect
			.element(screen.getByText('Your pantry is empty.', { exact: false }))
			.toBeVisible()
	})

	test('lists stocked items', async () => {
		itemsState.items = [
			{
				id: 'item-1',
				name: 'Olive oil',
				userId: 'user-1',
				createdAt: new Date(),
			},
		]

		const { screen } = await renderRoute({
			path: '/pantry',
			session: testSession,
		})

		await expect.element(screen.getByText('Olive oil')).toBeVisible()
		await expect.element(screen.getByText('Stocked')).toBeVisible()
	})
})
