import assert from 'node:assert/strict';
import test from 'node:test';

import {
  getReasoningEffortOptions,
  getReasoningModeOptions,
  OPENAI_CONFIG_MODEL_OPTIONS,
  OPENAI_GRADER_MODEL_OPTIONS,
  supportsReasoning,
  supportsReasoningMode,
} from '../src/lib/openaiModels.ts';

function flattenModelValues(
  groups: Array<{ models: Array<{ value: string }> }>,
): string[] {
  return groups.flatMap((group) => group.models.map((model) => model.value));
}

test('config model options include the latest OpenAI frontier models', () => {
  const values = flattenModelValues(OPENAI_CONFIG_MODEL_OPTIONS);

  assert.ok(values.includes('gpt-6.1-sol'));
  assert.ok(values.includes('gpt-5.6'));
  assert.ok(values.includes('gpt-5.6-sol'));
  assert.ok(values.includes('gpt-5.6-terra'));
  assert.ok(values.includes('gpt-5.6-luna'));
  assert.ok(values.includes('gpt-5.5'));
  assert.ok(values.includes('gpt-5.5-pro'));
  assert.ok(values.includes('gpt-5.4-pro'));
  assert.ok(values.includes('gpt-5.3-codex'));
  assert.ok(values.includes('gpt-5-pro'));
});

test('grader model options reuse Responses models and exclude Decisions-only models', () => {
  const configValues = flattenModelValues(OPENAI_CONFIG_MODEL_OPTIONS);
  const graderValues = flattenModelValues(OPENAI_GRADER_MODEL_OPTIONS);

  assert.equal(graderValues[0], '');
  assert.ok(configValues.includes('gpt-6-luna'));
  assert.deepEqual(graderValues.slice(1), configValues.filter((model) => model !== 'gpt-6-luna'));
});

test('Decisions model does not offer Responses reasoning controls', () => {
  assert.equal(supportsReasoning('gpt-6-luna'), false);
  assert.equal(supportsReasoningMode('gpt-6-luna'), false);
});

test('reasoning effort options reflect model-specific constraints', () => {
  assert.deepEqual(
    getReasoningEffortOptions('gpt-6.1-sol').map((option) => option.value),
    ['low', 'medium', 'high', 'xhigh', 'max'],
  );
  assert.deepEqual(
    getReasoningEffortOptions('gpt-5.6').map((option) => option.value),
    ['none', 'low', 'medium', 'high', 'xhigh'],
  );
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

test('reasoning mode options are only exposed for GPT-5.6 family models', () => {
  assert.deepEqual(
    getReasoningModeOptions('gpt-5.6-terra').map((option) => option.value),
    ['standard', 'pro'],
  );
  assert.equal(supportsReasoningMode('gpt-5.6-luna'), true);
  assert.equal(supportsReasoningMode('gpt-5.5'), false);
});
