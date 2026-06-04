import assert from 'node:assert/strict';
import test from 'node:test';

import {
  getReasoningEffortOptions,
  OPENAI_CONFIG_MODEL_OPTIONS,
  OPENAI_GRADER_MODEL_OPTIONS,
  supportsReasoning,
} from '../src/lib/openaiModels.ts';

function flattenModelValues(
  groups: Array<{ models: Array<{ value: string }> }>,
): string[] {
  return groups.flatMap((group) => group.models.map((model) => model.value));
}

test('config model options include the latest OpenAI frontier models', () => {
  const values = flattenModelValues(OPENAI_CONFIG_MODEL_OPTIONS);

  assert.ok(values.includes('gpt-5.5'));
  assert.ok(values.includes('gpt-5.5-pro'));
  assert.ok(values.includes('gpt-5.4-pro'));
  assert.ok(values.includes('gpt-5.3-codex'));
  assert.ok(values.includes('gpt-5-pro'));
});

test('grader model options reuse the config model catalog', () => {
  const configValues = flattenModelValues(OPENAI_CONFIG_MODEL_OPTIONS);
  const graderValues = flattenModelValues(OPENAI_GRADER_MODEL_OPTIONS);

  assert.equal(graderValues[0], '');
  assert.deepEqual(graderValues.slice(1), configValues);
});

test('reasoning effort options reflect model-specific constraints', () => {
  assert.deepEqual(
    getReasoningEffortOptions('gpt-5-pro').map((option) => option.value),
    ['high'],
  );
  assert.deepEqual(
    getReasoningEffortOptions('gpt-5.4-pro').map((option) => option.value),
    ['medium', 'high', 'xhigh'],
  );
  assert.deepEqual(
    getReasoningEffortOptions('gpt-5.5').map((option) => option.value),
    ['low', 'medium', 'high', 'xhigh'],
  );
  assert.equal(supportsReasoning('gpt-4.1'), false);
});
