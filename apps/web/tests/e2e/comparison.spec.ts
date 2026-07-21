import { test, expect } from '@playwright/test'

test.describe('comparison', () => {
  test.skip(!process.env.PLAYWRIGHT_E2E, 'Set PLAYWRIGHT_E2E=1 with stack running')

  test('comparisons page loads', async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[type="email"]', 'owner@agentlab.local')
    await page.fill('input[type="password"]', 'changeme')
    await page.click('button[type="submit"]')
    await page.goto('/comparisons')
    await expect(page.getByRole('heading', { name: 'Comparisons' })).toBeVisible()
  })
})
