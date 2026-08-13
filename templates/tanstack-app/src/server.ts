// Dev-only init: the --import flag used in prod (see package.json "start")
// is incompatible with the vp bin shim, so in dev the SDK loads through the
// SSR module graph instead. Deep auto-instrumentation (pg, etc.) only works
// via the prod path.
if (import.meta.env.DEV) {
	// @ts-expect-error side-effect-only .mjs outside the TS project
	await import('../instrument.server.mjs')
}

import { wrapFetchWithSentry } from '@sentry/tanstackstart-react'
import handler, { createServerEntry } from '@tanstack/react-start/server-entry'

export default createServerEntry(
	wrapFetchWithSentry({
		fetch(request: Request) {
			return handler.fetch(request)
		},
	}),
)
