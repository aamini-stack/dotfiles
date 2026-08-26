import {
	GetObjectCommand,
	PutObjectCommand,
	S3Client,
} from '@aws-sdk/client-s3'
import { getSignedUrl } from '@aws-sdk/s3-request-presigner'
import { createServerFn } from '@tanstack/react-start'
import { z } from 'zod'

import { serverEnv as env } from '@/env.server'

function getStorageClient() {
	return new S3Client({
		region: env.AWS_REGION,
		endpoint: env.AWS_ENDPOINT_URL,
		credentials: {
			accessKeyId: env.AWS_ACCESS_KEY_ID,
			secretAccessKey: env.AWS_SECRET_ACCESS_KEY,
		},
		forcePathStyle: true,
	})
}

export const getAvatarUrl = createServerFn({ method: 'GET' })
	.validator(z.object({ image: z.string().nullish() }))
	.handler(async ({ data }): Promise<string | undefined> => {
		if (!data.image) return undefined

		const isPublicUrl = /^https?:\/\//.test(data.image)
		if (isPublicUrl) return data.image

		const command = new GetObjectCommand({
			Bucket: env.AWS_S3_BUCKET_NAME,
			Key: data.image,
		})

		return getSignedUrl(getStorageClient(), command, { expiresIn: 60 * 60 })
	})

export const getAvatarUploadUrl = createServerFn({ method: 'POST' })
	.validator(z.object({ key: z.string().min(1).max(200) }))
	.handler(async ({ data }) => {
		const command = new PutObjectCommand({
			Bucket: env.AWS_S3_BUCKET_NAME,
			Key: data.key,
			ContentType: 'image/*',
		})
		return {
			url: await getSignedUrl(getStorageClient(), command, {
				expiresIn: 900,
			}),
		}
	})
