import { foreignKey, index, text, timestamp } from 'drizzle-orm/pg-core'
import { pgTable } from 'drizzle-orm/pg-core'

export * from './auth'
import { user } from './auth'

export const items = pgTable(
	'items',
	{
		id: text().primaryKey(),
		name: text().notNull(),
		userId: text().notNull(),
		createdAt: timestamp({ withTimezone: true }).notNull(),
	},
	(table) => [
		index('items_user_id_index').on(table.userId),
		foreignKey({
			columns: [table.userId],
			foreignColumns: [user.id],
			name: 'items_user_id_fk',
		}).onDelete('cascade'),
	],
)
