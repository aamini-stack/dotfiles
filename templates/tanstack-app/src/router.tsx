import { createRouter } from '@tanstack/react-router'

import { NotFoundComponent, ServerErrorComponent } from '@/components/errors'
import { queryClient } from '@/lib/utils/query'

import { routeTree } from './routeTree.gen'

export const getRouter = () =>
	createRouter({
		routeTree,
		scrollRestoration: true,
		defaultPreloadStaleTime: 0,
		context: { queryClient },
		defaultErrorComponent: ServerErrorComponent,
		defaultNotFoundComponent: NotFoundComponent,
	})
