import { createHash, randomUUID } from 'node:crypto'
import { mkdir, readFile, rename, rm, writeFile } from 'node:fs/promises'
import { execFile } from 'node:child_process'
import { promisify } from 'node:util'

import { tool, type Plugin } from '@opencode-ai/plugin'

const execFileAsync = promisify(execFile)
const temporaryRoot = '/tmp/opencode'
const workspaceCreation =
	/(?:\bjj\b[^;&|\n]*\b(?:workspace|ws)\s+add\b|\bwt\s+switch\b[^;&|\n]*(?:--create(?:=|\s|$)|-c(?:\s|$)))/m

function ownershipPath(directory: string) {
	const key = createHash('sha256').update(directory).digest('hex')
	return `${temporaryRoot}/.owners/${key}.json`
}

async function recordOwnership(input: {
	directory: string
	name: string
	sessionID: string
}) {
	const path = ownershipPath(input.directory)
	const temporary = `${path}.${process.pid}.tmp`
	await mkdir(`${temporaryRoot}/.owners`, { recursive: true })
	await writeFile(
		temporary,
		`${JSON.stringify({ ...input, createdAt: Date.now() }, null, 2)}\n`,
		{ mode: 0o600 },
	)
	await rename(temporary, path)
}

export default (async () => ({
	tool: {
		workspace_create: tool({
			description:
				'Create a temporary Jujutsu workspace owned by the current OpenCode session. Use this instead of jj workspace add or wt switch --create.',
			args: {
				name: tool.schema
					.string()
					.regex(/^[A-Za-z0-9._-]+(?:\/[A-Za-z0-9._-]+)*$/)
					.describe('Unique workspace name'),
				revision: tool.schema
					.string()
					.optional()
					.describe(
						'Jujutsu revision or revset. Defaults to the current revision.',
					),
			},
			async execute(args, context) {
				const command = ['switch', '--create', args.name]
				if (args.revision) command.push('--revision', args.revision)
				const resultPath = `${temporaryRoot}/.result-${process.pid}-${randomUUID()}`

				let commandError: unknown
				try {
					await execFileAsync('wt', command, {
						cwd: context.directory,
						env: {
							...process.env,
							JJ_WORKSPACE_ROOT: temporaryRoot,
							WT_RESULT_FILE: resultPath,
						},
					})
				} catch (error) {
					commandError = error
				}

				const directory = await readFile(resultPath, 'utf8')
					.then((value) => value.trim())
					.catch(() => '')
				await rm(resultPath, { force: true })
				if (!directory) {
					throw (
						commandError ??
						new Error('wt did not return the workspace directory')
					)
				}

				try {
					await recordOwnership({
						directory,
						name: args.name,
						sessionID: context.sessionID,
					})
				} catch (error) {
					try {
						await execFileAsync('wt', ['rm', '--yes', args.name], {
							cwd: context.directory,
						})
					} catch (rollbackError) {
						throw new AggregateError(
							[error, rollbackError],
							`Could not record or remove workspace ${args.name}`,
						)
					}
					throw error
				}
				if (commandError) throw commandError
				return {
					title: `Created workspace ${args.name}`,
					output: directory,
					metadata: { directory, sessionID: context.sessionID },
				}
			},
		}),
	},
	'tool.execute.before': async (input, output) => {
		if (input.tool !== 'bash') return
		const command = output.args?.command
		if (typeof command === 'string' && workspaceCreation.test(command)) {
			throw new Error(
				'Direct Jujutsu workspace creation is disabled. Use workspace_create.',
			)
		}
	},
})) satisfies Plugin
