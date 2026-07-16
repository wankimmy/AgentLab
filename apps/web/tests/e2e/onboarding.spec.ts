import { test, expect } from '@playwright/test'

test.describe('onboarding flow', () => {
  test.skip(!process.env.PLAYWRIGHT_E2E, 'Set PLAYWRIGHT_E2E=1 with docker compose stack running')

  test('login advances to onboarding step 1', async ({ page }) => {
    await page.goto('/login')
    await page.fill('#email', 'owner@agentlab.local')
    await page.fill('#password', 'changeme')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL(/\/onboarding/)
    await expect(page.getByText('Agent onboarding')).toBeVisible()
    await page.getByPlaceholder(/finance staff/i).fill('Help staff with ERP questions')
    await page.getByRole('button', { name: 'Help Me Define' }).click()
    await page.getByRole('checkbox').check()
    await page.getByRole('button', { name: 'Continue' }).click()
    await expect(page.getByText('Start empty')).toBeVisible()
    await page.goto('/templates')
    await expect(page.getByText('Templates')).toBeVisible()
  })
})
