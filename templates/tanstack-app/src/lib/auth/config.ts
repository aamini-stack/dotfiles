import { drizzleAdapter } from '@better-auth/drizzle-adapter'
import { betterAuth } from 'better-auth'
import { oAuthProxy } from 'better-auth/plugins'
import { tanstackStartCookies } from 'better-auth/tanstack-start'

import { db } from '@/db/connection'
import { account, session, user, verification } from '@/db/schema'
import { serverEnv as env } from '@/env.server'

const appOrigin = new URL(env.BETTER_AUTH_URL).origin

export function getAuth() {
	return betterAuth({
		appName: '__APP_NAME__',
		baseURL: {
			allowedHosts: [
				'127.0.0.1:*',
				'localhost:*',
				'__APP_NAME__-*.up.railway.app',
				'app-__APP_NAME__-*.up.railway.app',
			],
			protocol: 'auto',
			fallback: appOrigin,
		},
		secret: env.BETTER_AUTH_SECRET,
		database: drizzleAdapter(db, {
			provider: 'pg',
			schema: { account, session, user, verification },
		}),
		emailAndPassword: { enabled: true, autoSignIn: true },
		...(env.GOOGLE_CLIENT_ID && env.GOOGLE_CLIENT_SECRET
			? {
					socialProviders: {
						google: {
							clientId: env.GOOGLE_CLIENT_ID,
							clientSecret: env.GOOGLE_CLIENT_SECRET,
						},
					},
				}
			: {}),
		plugins: [
			oAuthProxy({
				productionURL: appOrigin,
				secret: env.BETTER_AUTH_SECRET,
			}),
			tanstackStartCookies(),
		],
	})
}
