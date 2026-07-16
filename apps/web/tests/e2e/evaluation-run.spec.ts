import { test, expect } from '@playwright/test'

test.describe('evaluation run flow', () => {
  test.skip(!process.env.PLAYWRIGHT_E2E, 'Set PLAYWRIGHT_E2E=1 with docker compose stack running')

  test('creates dataset and starts quick check', async ({ page }) => {
    await page.goto('/login')
    await page.fill('#email', 'owner@agentlab.local')
    await page.fill('#password', 'changeme')
    await page.click('button[type="submit"]')

    await page.goto('/evaluations/datasets')
    await page.getByPlaceholder('Dataset name').fill('E2E Eval Pack')
    await page.getByRole('button', { name: 'Create empty dataset' }).click()
    await expect(page).toHaveURL(/\/evaluations\/datasets\//)

    await page.getByPlaceholder('Name').fill('smoke-case')
    await page.getByPlaceholder('User message').fill('Hello eval')
    await page.getByRole('button', { name: 'Add case' }).click()
    await expect(page.getByText('smoke-case')).toBeVisible()

    await page.getByRole('link', { name: 'Run evaluation' }).click()
    await expect(page).toHaveURL('/evaluations/runs/new')
    await page.getByRole('button', { name: 'Estimate cost' }).click()
    await expect(page.getByRole('button', { name: 'Confirm and run' })).toBeVisible({
      timeout: 10000,
    })
    await page.getByRole('button', { name: 'Confirm and run' }).click()
    await expect(page).toHaveURL(/\/evaluations\/runs\//)
    await expect(page.getByText('Results')).toBeVisible()
  })
})
