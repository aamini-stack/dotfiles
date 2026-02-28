import type { Plugin } from "@opencode-ai/plugin"

export const CIEnforcePlugin: Plugin = async ({ $, client }) => {
	return {
		"session.idle": async () => {
			await client.app.log({
				body: { level: "info", message: "[ci-enforce] Running CI checks before session completes..." },
			})

			// Fast checks first: typecheck, lint, unit tests
			const fastChecks = await $`pnpm typecheck && pnpm lint && pnpm test:unit`.quiet()

			if (fastChecks.exitCode !== 0) {
				const output = fastChecks.stderr.toString() || fastChecks.stdout.toString()
				throw new Error(
					`[ci-enforce] FAST CHECKS FAILED (typecheck/lint/test:unit)\n\n${output}\n\nFix these issues before the session can complete.`
				)
			}

			await client.app.log({
				body: { level: "info", message: "[ci-enforce] Fast checks passed. Running e2e tests..." },
			})

			// E2E only if fast checks pass
			const e2e = await $`pnpm e2e`.quiet()

			if (e2e.exitCode !== 0) {
				const output = e2e.stderr.toString() || e2e.stdout.toString()
				throw new Error(
					`[ci-enforce] E2E TESTS FAILED\n\n${output}\n\nFix these issues before the session can complete.`
				)
			}

			await client.app.log({
				body: { level: "info", message: "[ci-enforce] All CI checks passed! Session can complete." },
			})
		},
	}
}
