import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { authClient } from '@/lib/auth/client'
import { redirectUnauthenticatedUsers } from '@/lib/auth/functions'
import { getAvatarUploadUrl, getAvatarUrl } from '@/lib/s3'

export const Route = createFileRoute('/(app)/profile')({
	beforeLoad: () => redirectUnauthenticatedUsers({ redirectTo: '/profile' }),
	component: Profile,
})
function Profile() {
	const session = authClient.useSession()
	const navigate = useNavigate()
	const [avatar, setAvatar] = useState<string>()
	const user = session.data?.user
	const upload = async (event: React.ChangeEvent<HTMLInputElement>) => {
		const file = event.target.files?.[0]
		if (!file || !user) return
		const key = `avatars/${user.id}-${crypto.randomUUID()}`
		const { url } = await getAvatarUploadUrl({ data: { key } })
		await fetch(url, {
			method: 'PUT',
			headers: { 'Content-Type': file.type },
			body: file,
		})
		await authClient.updateUser({ image: key })
		setAvatar(await getAvatarUrl({ data: { image: key } }))
	}
	return (
		<main className="mx-auto min-h-dvh max-w-xl space-y-8 p-6">
			<h1 className="text-4xl font-bold">Profile</h1>
			<div className="space-y-4">
				<p>{user?.name}</p>
				<p className="text-muted-foreground">{user?.email}</p>
				{avatar ? (
					<img
						src={avatar}
						alt="Profile avatar"
						className="size-24 rounded-full object-cover"
					/>
				) : null}
				<Input type="file" accept="image/*" onChange={upload} />
				<Button
					variant="outline"
					onClick={async () => {
						await authClient.signOut()
						await navigate({ to: '/' })
					}}
				>
					Sign out
				</Button>
			</div>
		</main>
	)
}
