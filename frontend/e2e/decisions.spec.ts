import { test, expect } from '@playwright/test';

const question = { type: 'predicate', name: 'relevant', instructions: 'Is it relevant?' };
const savedConfig = {
  id: 'decisions-test', name: 'Decision test', model: 'gpt-6-luna', system_prompt: '',
  temperature: 0.7, max_tokens: null, tools: [], tool_options: {}, tags: [],
  graders: [{ name: 'valid', type: 'json_schema', schema: { type: 'object' }, threshold: 1, weight: 1 }],
  concurrency: 5, readonly: false, reasoning_config: null, response_format: null,
  decision_config: { questions: [question] }, created_at: '', updated_at: '', comment: null,
};

test.beforeEach(async ({ page }) => {
  await page.route('http://127.0.0.1:5179/api/**', async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    const body = pathname === '/api/configs/decisions-test' ? savedConfig : [];
    await route.fulfill({ json: body });
  });
});

test('selecting Decisions shows question settings and switches back to Responses controls', async ({ page }) => {
  await page.goto('/configs/new');
  const form = page.locator('form');
  const model = page.locator('select').first();
  await expect(page.getByText('Temperature', { exact: true })).toBeVisible();
  await model.selectOption('gpt-6-luna');
  await expect(page.getByLabel('Questions (JSON)')).toBeVisible();
  for (const label of ['Temperature', 'Response Format', 'Tools', 'Reasoning Effort']) {
    await expect(form.getByText(label, { exact: true })).toHaveCount(0);
  }
  for (const type of ['choice', 'score', 'predicate']) {
    await page.getByRole('button', { name: `Load ${type} example` }).click();
    const questions = JSON.parse(await page.getByLabel('Questions (JSON)').inputValue());
    expect(questions[0].type).toBe(type);
  }
  await model.selectOption('gpt-4.1');
  await expect(page.getByLabel('Questions (JSON)')).toHaveCount(0);
  await expect(page.getByText('Response Format', { exact: true })).toBeVisible();
  await expect(form.getByText('Tools', { exact: true })).toBeVisible();
});

test('editing a Decisions configuration restores and saves questions', async ({ page }) => {
  let saved: Record<string, unknown> | undefined;
  await page.route('**/api/configs/decisions-test', async (route) => {
    if (route.request().method() === 'PUT') saved = route.request().postDataJSON();
    await route.fulfill({ json: savedConfig });
  });
  await page.goto('/configs/decisions-test/edit');
  const editor = page.getByLabel('Questions (JSON)');
  await expect(editor).toBeVisible();
  expect(JSON.parse(await editor.inputValue())).toEqual([question]);
  await editor.fill('{');
  await expect(page.getByRole('alert')).toContainText('valid JSON');
  const updated = { ...question, name: 'follow_up' };
  await editor.fill(JSON.stringify([updated]));
  await page.getByRole('button', { name: 'Save Changes' }).click();
  await expect(page).toHaveURL('/configs/decisions-test');
  expect(saved?.decision_config).toEqual({ questions: [updated] });
  expect(saved?.tools).toEqual([]);
  expect(saved?.reasoning_config).toBeNull();
  expect(saved?.response_format).toBeNull();
  await expect(page.getByText('Decisions API Questions', { exact: true })).toBeVisible();
  await expect(page.getByText('Temperature', { exact: true })).toHaveCount(0);
});

test('creating a Decisions configuration saves the API-specific payload', async ({ page }) => {
  let saved: Record<string, unknown> | undefined;
  await page.route('**/api/configs', async (route) => {
    saved = route.request().postDataJSON();
    await route.fulfill({ json: savedConfig });
  });
  await page.goto('/configs/new');
  await page.getByPlaceholder('My eval config').fill('Decision eval');
  await page.locator('select').first().selectOption('gpt-6-luna');
  await page.getByRole('button', { name: 'Add Grader' }).click();
  await page.getByPlaceholder('Grader name').fill('valid');
  await expect(page.getByText('Default prompt grader model: gpt-4.1')).toBeVisible();
  await page.locator('select').nth(1).selectOption('string_check');
  await page.getByLabel('Questions (JSON)').fill(JSON.stringify([question]));
  await page.getByRole('button', { name: 'Create Config', exact: true }).click();
  await expect(page).toHaveURL('/configs/decisions-test');
  expect(saved?.model).toBe('gpt-6-luna');
  expect(saved?.decision_config).toEqual({ questions: [question] });
  expect(saved?.tools).toEqual([]);
  expect(saved?.reasoning_config).toBeNull();
  expect(saved?.response_format).toBeNull();
});
