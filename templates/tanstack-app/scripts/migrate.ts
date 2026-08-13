import { existsSync } from 'node:fs'

import { sql } from 'drizzle-orm'
import { migrate } from 'drizzle-orm/node-postgres/migrator'

import { closeDb, db } from '../src/db/connection'
import { REQUIRED_EXTENSIONS } from '../src/db/extensions'

// Wraps drizzle-orm's migrator instead of `drizzle-kit migrate` because the
// CLI swallows the underlying Postgres error (just exits 1), which makes
// failures invisible in deploy logs. This prints the full error.
async function main() {
	if (!existsSync('src/db/migrations')) {
		console.log('No migrations found; run db:generate or db:push.')
		await closeDb()
		return
	}

	console.log('Running migrations...')
	try {
		for (const ext of REQUIRED_EXTENSIONS) {
			await db.execute(sql`CREATE EXTENSION IF NOT EXISTS ${sql.raw(ext)}`)
		}
		await migrate(db, { migrationsFolder: 'src/db/migrations' })
		console.log('Migrations complete.')
	} catch (error) {
		console.error('Migration failed:', error)
		process.exitCode = 1
	} finally {
		await closeDb()
	}
}

void main()
