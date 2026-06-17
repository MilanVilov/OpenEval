import assert from 'node:assert/strict';
import test from 'node:test';

import {
  getNextGraderSort,
  sortResultsByGrader,
} from '../src/pages/runs/runDetailSorting.ts';

interface TestResult {
  id: string;
  comparer_details: Record<string, unknown> | null;
}

const results: TestResult[] = [
  {
    id: 'pass-a',
    comparer_details: {
      safety: { passed: true },
    },
  },
  {
    id: 'fail-a',
    comparer_details: {
      safety: { passed: false },
    },
  },
  {
    id: 'missing',
    comparer_details: null,
  },
  {
    id: 'informational',
    comparer_details: {
      safety: { passed: null },
    },
  },
  {
    id: 'pass-b',
    comparer_details: {
      safety: { passed: true },
    },
  },
  {
    id: 'fail-b',
    comparer_details: {
      safety: { passed: false },
    },
  },
];

test('getNextGraderSort cycles through fail first, pass first, and unsorted', () => {
  const failFirst = getNextGraderSort(null, 'safety');
  assert.deepEqual(failFirst, { graderName: 'safety', direction: 'fail-first' });

  const passFirst = getNextGraderSort(failFirst, 'safety');
  assert.deepEqual(passFirst, { graderName: 'safety', direction: 'pass-first' });

  const cleared = getNextGraderSort(passFirst, 'safety');
  assert.equal(cleared, null);
});

test('sortResultsByGrader groups failed rows before passed rows', () => {
  const sorted = sortResultsByGrader(results, {
    graderName: 'safety',
    direction: 'fail-first',
  });

  assert.deepEqual(
    sorted.map((result) => result.id),
    ['fail-a', 'fail-b', 'pass-a', 'pass-b', 'missing', 'informational'],
  );
});

test('sortResultsByGrader groups passed rows before failed rows', () => {
  const sorted = sortResultsByGrader(results, {
    graderName: 'safety',
    direction: 'pass-first',
  });

  assert.deepEqual(
    sorted.map((result) => result.id),
    ['pass-a', 'pass-b', 'fail-a', 'fail-b', 'missing', 'informational'],
  );
});
