import { createServerFn } from '@tanstack/react-start'
import { getRequestHeaders } from '@tanstack/react-start/server'

import { getAuth } from './config'

export const getCurrentSession = createServerFn({ method: 'GET' }).handler(() =>
	getAuth().api.getSession({ headers: getRequestHeaders() }),
)
