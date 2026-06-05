import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildDisplayRow,
  buildDisplayRows,
  rowHasTranslatedChanges,
  toggleOriginalRowIndexes,
  type TranslatedPageState,
} from '../src/lib/translatedPageRows.ts';

interface TestRow {
  [key: string]: string;
  actual_output: string;
  expected_output: string;
  input: string;
}

const baseRows: TestRow[] = [
  { input: 'Question 1', expected_output: 'Answer 1', actual_output: 'Actual 1' },
  { input: 'Question 2', expected_output: 'Answer 2', actual_output: 'Actual 2' },
];

const translationState: TranslatedPageState<TestRow> = {
  originalRows: baseRows,
  originalRowIndexes: [1],
  targetLanguage: 'Dutch',
  translatedRows: [
    { input: 'Vraag 1', expected_output: 'Antwoord 1', actual_output: 'Werkelijk 1' },
    { input: 'Vraag 2', expected_output: 'Antwoord 2', actual_output: 'Werkelijk 2' },
  ],
};

test('buildDisplayRow returns the translated row when original view is off', () => {
  assert.deepEqual(buildDisplayRow(baseRows[0], 0, translationState), translationState.translatedRows[0]);
});

test('buildDisplayRows restores original rows for toggled indexes', () => {
  assert.deepEqual(buildDisplayRows(baseRows, translationState), [
    translationState.translatedRows[0],
    translationState.originalRows[1],
  ]);
});

test('rowHasTranslatedChanges checks all translated fields', () => {
  assert.equal(
    rowHasTranslatedChanges(translationState, 0, ['input', 'expected_output', 'actual_output']),
    true,
  );
  assert.equal(
    rowHasTranslatedChanges(
      {
        ...translationState,
        translatedRows: [
          translationState.originalRows[0],
          translationState.originalRows[1],
        ],
      },
      1,
      ['input', 'expected_output'],
    ),
    false,
  );
});

test('toggleOriginalRowIndexes flips the selected row membership', () => {
  assert.deepEqual(toggleOriginalRowIndexes([1], 0), [1, 0]);
  assert.deepEqual(toggleOriginalRowIndexes([1], 1), []);
});
