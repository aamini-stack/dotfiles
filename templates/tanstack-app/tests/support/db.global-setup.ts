import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import type { TestProject } from 'vitest/node'

import { REQUIRED_EXTENSIONS } from '@/db/extensions'

declare module 'vitest' {
	interface ProvidedContext {
		dbUri: string
	}
}

const migrationsFolder = fileURLToPath(
	new URL('../../src/db/migrations', import.meta.url),
)

export default async function setup(project: TestProject) {
	const { PostgreSqlContainer } = await import('@testcontainers/postgresql')
	const { Wait } = await import('testcontainers')
	const { drizzle } = await import('drizzle-orm/node-postgres')
	const { migrate } = await import('drizzle-orm/node-postgres/migrator')
	const { Pool } = await import('pg')

	const container = await new PostgreSqlContainer(
		process.env.TEST_DB_IMAGE ?? 'postgres:17',
	)
		.withWaitStrategy(Wait.forHealthCheck())
		.start()

	try {
		if (existsSync(migrationsFolder)) {
			const client = new Pool({
				connectionString: container.getConnectionUri(),
			})
			try {
				const db = drizzle({ client })
				for (const ext of REQUIRED_EXTENSIONS) {
					await db.execute(`CREATE EXTENSION IF NOT EXISTS "${ext}"`)
				}
				await migrate(db, { migrationsFolder })
			} finally {
				await client.end()
			}
		}
	} catch (error) {
		await container.stop()
		throw error
	}

	project.provide('dbUri', container.getConnectionUri())

	return async () => {
		await container.stop()
	}
}
