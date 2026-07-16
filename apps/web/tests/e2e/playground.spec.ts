import { test, expect } from '@playwright/test'

test.describe('playground flow', () => {
  test.skip(!process.env.PLAYWRIGHT_E2E, 'Set PLAYWRIGHT_E2E=1 with docker compose stack running')

  test('streams mock response in playground', async ({ page }) => {
    await page.goto('/login')
    await page.fill('#email', 'owner@agentlab.local')
    await page.fill('#password', 'changeme')
    await page.click('button[type="submit"]')
    await page.goto('/agents/new')
    await page.fill('#name', 'E2E Playground Agent')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL(/\/agents\//)
    await page.getByRole('link', { name: 'Open playground' }).click()
    await page.getByPlaceholder('Type a message...').fill('Hello playground')
    await page.getByRole('button', { name: 'Send' }).click()
    await expect(page.getByText('[mock:')).toBeVisible({ timeout: 15000 })
    await expect(page.getByText('Duration')).toBeVisible()
  })
})
