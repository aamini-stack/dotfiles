import '@tests/support/mocks/browser'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
	createMemoryHistory,
	createRootRoute,
	createRouter,
	RouterProvider,
} from '@tanstack/react-router'
import type { ReactElement } from 'react'
import { render, type RenderResult } from 'vitest-browser-react'

export interface RenderComponentOptions {
	element: ReactElement
	queryClient?: QueryClient
	setup?: () => Promise<void> | void
}

type TestRouter = {
	state: { location: { pathname: string } }
}

export function createTestQueryClient() {
	return new QueryClient({
		defaultOptions: {
			queries: { retry: false, refetchOnWindowFocus: false },
			mutations: { retry: false },
		},
	})
}

export async function renderComponent(
	options: RenderComponentOptions,
): Promise<RenderResult & { router: TestRouter }> {
	const queryClient = options.queryClient ?? createTestQueryClient()

	localStorage.clear()
	document.body.replaceChildren()
	await options.setup?.()

	const container = document.body.appendChild(document.createElement('div'))
	container.style.width = '100vw'
	container.style.minHeight = '100vh'

	const element = options.element
	const rootRoute = createRootRoute({
		component: () => element,
	})
	const router = createRouter({
		routeTree: rootRoute,
		history: createMemoryHistory({ initialEntries: ['/'] }),
		defaultPreloadStaleTime: 0,
		context: { queryClient },
	})

	const result = await render(
		<QueryClientProvider client={queryClient}>
			<RouterProvider router={router} />
		</QueryClientProvider>,
		{ container },
	)

	return Object.assign(result, { router })
}
