import { existsSync } from 'node:fs'
import { dirname, resolve } from 'node:path'

import type { NodePgDatabase } from 'drizzle-orm/node-postgres'
import type { Pool } from 'pg'
import { inject } from 'vite-plus/test'

import { test as baseTest } from './server'

const DEFAULT_SCHEMA_PATH = 'src/db/schema/index.ts'
const ROOT_MARKERS = [
	'vite.config.ts',
	'vite.config.mts',
	'vite.config.js',
	'vite.config.mjs',
	'vitest.config.ts',
	'vitest.config.mts',
	'vitest.config.js',
	'vitest.config.mjs',
]

export interface DbConfig {
	root?: string
	schemaPath?: string
}

export type Database = NodePgDatabase & {
	$client: Pool
}

export interface DbFixture {
	db: Database
	seedFunction: (db: Database) => Promise<void> | void
}

let dbConfig: DbConfig = {}
let seedFunction: (db: Database) => Promise<void> | void = async () => {}

function findProjectRoot(start = process.cwd()) {
	let directory = start

	while (true) {
		if (ROOT_MARKERS.some((marker) => existsSync(resolve(directory, marker)))) {
			return directory
		}

		const parent = dirname(directory)
		if (parent === directory) return start
		directory = parent
	}
}

export const test = baseTest.extend<DbFixture>({
	seedFunction: [
		async ({}, use) => {
			await use(seedFunction)
		},
		{ scope: 'file' },
	],
	db: [
		async ({ seedFunction }, use) => {
			const { drizzle } = await import('drizzle-orm/node-postgres')
			const { Pool } = await import('pg')
			const root = dbConfig.root ?? findProjectRoot()
			const schemaPath = resolve(
				root,
				dbConfig.schemaPath ?? DEFAULT_SCHEMA_PATH,
			)
			const client = new Pool({ connectionString: inject('dbUri') })
			const db = Object.assign(drizzle({ client }), {
				$client: client,
			})

			try {
				await resetDatabase(db, { schemaPath, seedFunction })
				await use(db)
			} finally {
				await db.$client.end()
			}
		},
		{ scope: 'file' },
	],
})

export { afterEach, beforeEach, describe, expect, vi } from 'vite-plus/test'

export function initDb(
	seed: (db: Database) => Promise<void> | void,
	config: DbConfig = {},
) {
	dbConfig = config
	seedFunction = seed
}

export interface ResetDatabaseOptions {
	schemaPath: string
	seedFunction?: (db: Database) => Promise<void> | void
}

export async function resetDatabase(
	db: Database,
	{ schemaPath, seedFunction }: ResetDatabaseOptions,
) {
	const { reset } = await import('drizzle-seed')
	const schema = await import(/* @vite-ignore */ schemaPath)

	await reset(db, schema)
	if (seedFunction) await seedFunction(db)
}
