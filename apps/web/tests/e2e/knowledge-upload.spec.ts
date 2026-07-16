import { test, expect } from '@playwright/test'

test.describe('knowledge upload', () => {
  test.skip(!process.env.PLAYWRIGHT_E2E, 'Set PLAYWRIGHT_E2E=1 to run E2E tests')

  test('creates collection and shows upload UI', async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[type="email"]', 'owner@agentlab.local')
    await page.fill('input[type="password"]', 'changeme')
    await page.click('button[type="submit"]')
    await page.waitForURL(/dashboard|onboarding/)

    await page.goto('/knowledge')
    await expect(page.getByRole('heading', { name: 'Knowledge' })).toBeVisible()
    await page.fill('input[placeholder="Collection name"]', 'E2E Collection')
    await page.click('button:has-text("Create collection")')
    await expect(page.getByText('Upload documents')).toBeVisible()
  })
})
