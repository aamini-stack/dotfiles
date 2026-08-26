// Extensions provisioned before every migrate run (scripts/migrate.ts) and
// before test-container seeding (tests/support/fixtures/db.ts). drizzle-kit
// never emits CREATE EXTENSION, so they live outside the migration files.
export const REQUIRED_EXTENSIONS = ['pg_trgm', 'citext'] as const
