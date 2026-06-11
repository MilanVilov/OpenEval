import assert from 'node:assert/strict';
import test from 'node:test';

import { getResultStatusBadge } from '../src/lib/resultStatus.ts';

test('getResultStatusBadge prioritizes errors over score-only state', () => {
  assert.deepEqual(
    getResultStatusBadge(null, 'LLM call failed'),
    { variant: 'error', label: 'Error' },
  );
});

test('getResultStatusBadge renders score-only when no error is present', () => {
  assert.deepEqual(
    getResultStatusBadge(null, null),
    { variant: 'default', label: 'Score only' },
  );
});

test('getResultStatusBadge renders pass and fail judgments', () => {
  assert.deepEqual(
    getResultStatusBadge(true, null),
    { variant: 'success', label: 'Pass' },
  );
  assert.deepEqual(
    getResultStatusBadge(false, null),
    { variant: 'error', label: 'Fail' },
  );
});
