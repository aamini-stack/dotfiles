import { expect, test } from '@playwright/test'

test('landing page renders', async ({ page }) => {
	await page.goto('/')
	await expect(page.getByText('__APP_NAME__', { exact: true })).toBeVisible()
	await page.goto('/auth/login')
	await expect(page.getByText('Sign in', { exact: true })).toBeVisible()
})
