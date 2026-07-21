import { test, expect } from '@playwright/test'

test.describe('release check', () => {
  test.skip(!process.env.PLAYWRIGHT_E2E, 'Set PLAYWRIGHT_E2E=1 with stack running')

  test('agent detail shows release actions', async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[type="email"]', 'owner@agentlab.local')
    await page.fill('input[type="password"]', 'changeme')
    await page.click('button[type="submit"]')
    await page.goto('/agents')
    await page.locator('a').filter({ hasText: /agent/i }).first().click()
    await expect(page.getByText('Release check')).toBeVisible()
  })
})
