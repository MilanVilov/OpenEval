import assert from 'node:assert/strict';
import test from 'node:test';

import type { EvalResult } from '../src/types/run.ts';
import {
  buildRunSourceRows,
  buildRunTranslationScope,
  getRunInputForDisplay,
  type RunResultTranslationState,
} from '../src/pages/runs/runDetailTranslations.ts';

const results: EvalResult[] = [
  {
    id: 'r1',
    eval_run_id: 'run-1',
    row_index: 0,
    input_data: 'Question 1',
    expected_output: 'Answer 1',
    actual_output: 'Actual 1',
    comparer_score: 1,
    comparer_details: null,
    passed: true,
    latency_ms: 10,
    token_usage: { input_tokens: 1, output_tokens: 1 },
    error: null,
    created_at: '2026-06-04T10:00:00Z',
  },
  {
    id: 'r2',
    eval_run_id: 'run-1',
    row_index: 1,
    input_data: 'Question 2',
    expected_output: 'Answer 2',
    actual_output: 'Actual 2',
    comparer_score: 0,
    comparer_details: null,
    passed: false,
    latency_ms: 10,
    token_usage: { input_tokens: 1, output_tokens: 1 },
    error: null,
    created_at: '2026-06-04T10:00:00Z',
  },
];

test('buildRunTranslationScope keys state by ordered result ids', () => {
  assert.equal(buildRunTranslationScope(results), '["r1","r2"]');
});

test('buildRunSourceRows keeps original inputs when a page was already translated', () => {
  const translationState: RunResultTranslationState = {
    resultIds: ['r1', 'r2'],
    originalInputs: ['Question 1', 'Question 2'],
    originalInputRowIndexes: [],
    targetLanguage: 'Dutch',
    translatedInputs: ['Vraag 1', 'Vraag 2'],
  };

  assert.deepEqual(buildRunSourceRows(results, translationState), [
    { input: 'Question 1' },
    { input: 'Question 2' },
  ]);
});

test('getRunInputForDisplay switches between original and translated inputs per row', () => {
  const translationState: RunResultTranslationState = {
    resultIds: ['r1', 'r2'],
    originalInputs: ['Question 1', 'Question 2'],
    originalInputRowIndexes: [1],
    targetLanguage: 'Dutch',
    translatedInputs: ['Vraag 1', 'Vraag 2'],
  };

  assert.equal(getRunInputForDisplay(results[0], 0, translationState), 'Vraag 1');
  assert.equal(getRunInputForDisplay(results[1], 1, translationState), 'Question 2');
  assert.equal(getRunInputForDisplay(results[0], 0, null), 'Question 1');
});
