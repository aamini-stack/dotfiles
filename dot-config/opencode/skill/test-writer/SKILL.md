---
name: test-driven-development
description: Writing unit, integration, or E2E for any @aamini-stack app/project
compatibility: opencode
metadata:
  audience: developers
  frameworks: vitest, vitest-browser, playwright, drizzle, msw
---

## What I do

- Assist with writing high quality tests for any accompanying feature work.
- Make sure all tests provide value and follow repository standards.
- Write unit, integration, and E2E tests depending on the feature/granularity.

## When to use me

Use this skill when you are doing TDD or feature work and need assistance
writing high quality tests.

## Test Commands

Run tests from the app directory (e.g., `cd apps/paas`):

| Command                 | Action                                  |
| :---------------------- | :-------------------------------------- |
| `pnpm test:unit`        | Run unit tests                          |
| `pnpm test:integration` | Run integration tests (browser, server) |
| `pnpm e2e`              | Run E2E tests                           |
| `pnpm e2e:update`       | Update E2E screenshots                  |

## Unit Tests (`*.test.unit.ts`)

- Plain node environment for pure functions
- No external dependencies (network, database, browser)
- Fast, isolated tests
- Test your own business logic, not library functions

Example (rate limiter with fake timers):

```ts
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { RateLimiter } from './rate-limiter'

const TEST_IP = '192.168.1.1'
let limiter: RateLimiter

beforeEach(() => {
	limiter = new RateLimiter()
	vi.useFakeTimers()
	vi.setSystemTime(0)
})

afterEach(() => {
	vi.useRealTimers()
})

describe('RateLimiter', () => {
	test('Block after limit is reached', () => {
		expect(limiter.consume(TEST_IP)).toEqual({ success: true, remaining: 2 })
		expect(limiter.consume(TEST_IP)).toEqual({ success: true, remaining: 1 })
		expect(limiter.consume(TEST_IP)).toEqual({ success: true, remaining: 0 })
		expect(limiter.consume(TEST_IP)).toEqual({ success: false, retryAfter: 15 })
		vi.advanceTimersByTime(15 * 60 * 1000 + 1)
		expect(limiter.consume(TEST_IP)).toEqual({ success: true, remaining: 0 })
	})

	test('Refill tokens after cooldown', () => {
		expect(limiter.consume(TEST_IP)).toEqual({ success: true, remaining: 2 })
		vi.advanceTimersByTime(15 * 60 * 1000 + 1)
		expect(limiter.consume(TEST_IP)).toEqual({ success: true, remaining: 2 })
	})

	test("Don't fill tokens before window passes", () => {
		expect(limiter.consume(TEST_IP)).toEqual({ success: true, remaining: 2 })
		vi.advanceTimersByTime(14 * 60 * 1000)
		expect(limiter.consume(TEST_IP)).toEqual({ success: true, remaining: 1 })
	})

	test('Handling multiple IPs independently', () => {
		const ip1 = '192.168.1.1'
		const ip2 = '192.168.1.2'
		expect(limiter.consume(ip1)).toEqual({ success: true, remaining: 2 })
		expect(limiter.consume(ip2)).toEqual({ success: true, remaining: 2 })
	})
})
```

## Database Tests (`*.test.ts`)

1. Use db test fixture: `import { test } from '@/mocks/test-extend-db'`
2. Optional: Use `initDb()` to seed test data:

```ts
import { test, initDb } from '@/mocks/test-extend-db'
import { describe, expect } from 'vitest'
import { shows } from './__fixtures__/shows'
import { show } from '@/db/tables'

describe('search tests', () => {
	// Seed database with test data from fixtures
	initDb(async (db) => {
		await db.insert(show).values(shows)
	})

	test('exact title', async ({ db }) => {
		const results = await fetchSuggestions(db, 'Game of Thrones')
		expect(results[0]).toEqual({
			title: 'Game of Thrones',
			imdbId: 'tt0944947',
			rating: 9.2,
		})
	})
})
```

## Browser Tests (`*.test.tsx`)

- vitest-browser with real Playwright browser
- Test React components in isolation
- Import test extension: `import { test } from '@/mocks/test-extend-browser'`
- Use `vitest-browser-react` for component rendering
- Use `userEvent` from `vitest/browser` for interactions
- Use `expect.element()` for async assertions

Example:

```ts
import { test } from '@/mocks/test-extend-browser'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
	createRootRoute,
	createRoute,
	createRouter,
	RouterContextProvider,
} from '@tanstack/react-router'
import { http, HttpResponse } from 'msw'
import { beforeEach, describe, expect, vi } from 'vitest'
import { render } from 'vitest-browser-react'
import { page, userEvent } from 'vitest/browser'
import { SearchBar } from './search-bar'

const testQueryClient = new QueryClient({
	defaultOptions: {
		queries: {
			retry: false,
		},
	},
})

vi.mock(import('@/lib/react-query'), () => ({
	queryClient: testQueryClient,
}))

beforeEach(() => {
	testQueryClient.clear()
})

function MockRouter(props: { children: React.ReactNode }) {
	const rootRoute = createRootRoute()
	const indexRoute = createRoute({
		getParentRoute: () => rootRoute,
		path: '/',
	})
	const routeTree = rootRoute.addChildren([indexRoute])
	const router = createRouter({ routeTree })

	return (
		<QueryClientProvider client={testQueryClient}>
			<RouterContextProvider router={router}>
				{props.children}
			</RouterContextProvider>
		</QueryClientProvider>
	)
}

test('basic search', async () => {
	const screen = await render(<SearchBar />, {
		wrapper: MockRouter,
	})

	const searchBar = screen.getByRole('combobox')
	await userEvent.fill(searchBar, 'avatar')
	await expect
		.element(page.getByText(/Avatar: The Last Airbender/).first())
		.toBeVisible()
})

test('no results', async ({ worker }) => {
	worker.use(
		http.get('/api/suggestions', () => {
			return HttpResponse.json([])
		}),
	)

	const screen = await render(<SearchBar />, {
		wrapper: MockRouter,
	})
	const searchBar = screen.getByRole('combobox')
	await userEvent.fill(searchBar, 'blah')
	await expect.element(screen.getByText(/No TV Shows Found./i)).toBeVisible()
})

test('error message', async ({ worker }) => {
	worker.use(
		http.get('/api/suggestions', () => {
			return HttpResponse.error()
		}),
	)

	const screen = await render(<SearchBar />, {
		wrapper: MockRouter,
	})
	const searchBar = screen.getByRole('combobox')
	await userEvent.fill(searchBar, 'error')
	await expect
		.element(screen.getByText(/Something went wrong. Please try again./i))
		.toBeVisible()
})
```

## Mocking APIs with MSW

1\. Set up mock JSON responses in `__mocks__/data/suggestions.json`:

```json
[
	{
		"imdbId": "tt0417299",
		"title": "Avatar: The Last Airbender",
		"startYear": "2005",
		"endYear": "2008",
		"rating": 9.3,
		"numVotes": 410746
	},
	{
		"imdbId": "tt9018736",
		"title": "Avatar: The Last Airbender",
		"startYear": "2024",
		"endYear": null,
		"rating": 7.2,
		"numVotes": 80299
	},
	{
		"imdbId": "tt10732794",
		"title": "The King's Avatar",
		"startYear": "2019",
		"endYear": "2019",
		"rating": 8.1,
		"numVotes": 1776
	},
	{
		"imdbId": "tt6859260",
		"title": "The King's Avatar",
		"startYear": "2017",
		"endYear": null,
		"rating": 7.4,
		"numVotes": 1617
	},
	{
		"imdbId": "tt15776622",
		"title": "Avataro Sentai Donbrothers",
		"startYear": "2022",
		"endYear": "2023",
		"rating": 8.1,
		"numVotes": 345
	}
]
```

2\. Set up handlers `__mocks__/handlers.ts`:

```ts
import suggestions from '@/mocks/data/suggestions.json' with { type: 'json' }
import { http, HttpResponse } from 'msw'

export default [
	http.get('/api/suggestions', () => {
		return HttpResponse.json(suggestions)
	}),
]
```

3\. Import `@/mocks/test-extend-server` if a server test (.ts) or
`@/mocks/test-extend-browser` if a browser test (.tsx):

```ts
import { test } from '@/mocks/test-extend-server'
import { describe, expect } from 'vitest'
import { fetchGitHubRepos } from './github-repos'

describe('GitHub Repositories', () => {
	test('fetches repositories from GitHub API', async () => {
		const repos = await fetchGitHubRepos('test_token')
		expect(repos).toHaveLength(3)
		expect(repos[0].name).toBe('test-repo')
	})
})
```

4\. (Optional): Setup inline mocks (For error scenarios or one-off requests):

```ts
import { test } from '@/mocks/test-extend-browser'
import { describe, expect } from 'vitest'
import { fetchGitHubRepos } from './github-repos'

test('no results', async ({ worker }) => {
	// One-off mock for error scenario
	worker.use(
		http.get('/api/suggestions', () => {
			return HttpResponse.json([])
		}),
	)

	const screen = await render(<SearchBar />, {
		wrapper: MockRouter,
	})
	const searchBar = screen.getByRole('combobox')
	await userEvent.fill(searchBar, 'blah')
	await expect.element(screen.getByText(/No TV Shows Found./i)).toBeVisible()
})
```

## E2E Tests (Playwright)

- Full browser automation tests
- Located in `e2e/` directory
- Test user flows and page interactions
- Use screenshots for visual regression testing

Example:

```ts
import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
	await page.goto('/', { waitUntil: 'networkidle' })
})

test('search bar click navigation works', async ({ page }) => {
	const searchBar = page.getByRole('combobox')
	await searchBar.click()
	await searchBar.fill('Avatar')
	await page.getByTestId('loading-spinner').waitFor({ state: 'hidden' })
	const avatarDropdownOption = page.getByText('Avatar: The Last Airbender')
	await expect(avatarDropdownOption).toBeVisible()
	await avatarDropdownOption.click()
	await expect(page).toHaveURL(/.*\/ratings\/tt0417299/)
})

test('Screenshot Homepage', async ({ page }) => {
	await expect(page).toHaveScreenshot()
})
```
