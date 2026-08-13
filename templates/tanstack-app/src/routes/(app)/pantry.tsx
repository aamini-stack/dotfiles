import { createFileRoute, useRouter } from '@tanstack/react-router'
import { motion } from 'framer-motion'
import { useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { redirectUnauthenticatedUsers } from '@/lib/auth/functions'
import { createItem, deleteItem, listItems } from '@/lib/items/server'

export const Route = createFileRoute('/(app)/pantry')({
	beforeLoad: () => redirectUnauthenticatedUsers({ redirectTo: '/pantry' }),
	loader: () => listItems(),
	component: Pantry,
})

function Pantry() {
	const items = Route.useLoaderData()
	const router = useRouter()
	const [name, setName] = useState('')
	const add = async (event: React.FormEvent<HTMLFormElement>) => {
		event.preventDefault()
		if (!name.trim()) return
		await createItem({ data: { name } })
		setName('')
		await router.invalidate()
	}
	return (
		<main className="mx-auto min-h-dvh w-full max-w-2xl space-y-8 p-6">
			<header>
				<p className="text-muted-foreground text-sm tracking-[0.2em] uppercase">
					Your kitchen
				</p>
				<h1 className="text-4xl font-bold">Pantry</h1>
			</header>
			<Card>
				<CardContent className="pt-6">
					<form onSubmit={add} className="flex gap-3">
						<Input
							aria-label="Item name"
							placeholder="Add an ingredient"
							value={name}
							onChange={(event) => setName(event.target.value)}
						/>
						<Button>Add item</Button>
					</form>
				</CardContent>
			</Card>
			{items.length ? (
				<div className="space-y-3">
					{items.map((item) => (
						<motion.div
							key={item.id}
							initial={{ opacity: 0, x: -12 }}
							animate={{ opacity: 1, x: 0 }}
						>
							<Card>
								<CardContent className="flex items-center justify-between py-4">
									<div className="flex items-center gap-3">
										<Badge variant="secondary">Stocked</Badge>
										<span>{item.name}</span>
									</div>
									<Button
										variant="ghost"
										size="sm"
										onClick={async () => {
											await deleteItem({ data: { id: item.id } })
											await router.invalidate()
										}}
									>
										Delete
									</Button>
								</CardContent>
							</Card>
						</motion.div>
					))}
				</div>
			) : (
				<p className="text-muted-foreground py-12 text-center">
					Your pantry is empty. Add something delicious.
				</p>
			)}
		</main>
	)
}
