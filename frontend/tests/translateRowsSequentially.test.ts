import assert from 'node:assert/strict';
import test from 'node:test';

import {
  translateRowsSequentially,
  type RowTranslationProgress,
} from '../src/lib/translateRowsSequentially.ts';

test('translateRowsSequentially translates rows in order and reports progress', async () => {
  const rows = [
    { input: 'Question 1', expected_output: 'Answer 1' },
    { input: 'Question 2', expected_output: 'Answer 2' },
    { input: 'Question 3', expected_output: 'Answer 3' },
  ];
  const translationOrder: string[] = [];
  const translatedRowsSeen: Array<{ rowIndex: number; input: string }> = [];
  const progressUpdates: RowTranslationProgress[] = [];

  const translatedRows = await translateRowsSequentially({
    rows,
    targetLanguage: 'English',
    translateRow: async (row, targetLanguage) => {
      translationOrder.push(row.input);
      return {
        ...row,
        input: `${targetLanguage}:${row.input}`,
      };
    },
    onProgress: (progress) => {
      progressUpdates.push({ ...progress });
    },
    onRowTranslated: (rowIndex, translatedRow) => {
      translatedRowsSeen.push({
        rowIndex,
        input: translatedRow.input,
      });
    },
  });

  assert.deepEqual(translationOrder, ['Question 1', 'Question 2', 'Question 3']);
  assert.deepEqual(translatedRowsSeen, [
    { rowIndex: 0, input: 'English:Question 1' },
    { rowIndex: 1, input: 'English:Question 2' },
    { rowIndex: 2, input: 'English:Question 3' },
  ]);
  assert.deepEqual(progressUpdates, [
    { activeRowIndex: 0, completed: 0, total: 3 },
    { activeRowIndex: 1, completed: 1, total: 3 },
    { activeRowIndex: 2, completed: 2, total: 3 },
    { activeRowIndex: null, completed: 3, total: 3 },
  ]);
  assert.deepEqual(translatedRows, [
    { input: 'English:Question 1', expected_output: 'Answer 1' },
    { input: 'English:Question 2', expected_output: 'Answer 2' },
    { input: 'English:Question 3', expected_output: 'Answer 3' },
  ]);
});

test('translateRowsSequentially returns early for empty pages', async () => {
  let translateCalls = 0;
  const progressUpdates: RowTranslationProgress[] = [];

  const translatedRows = await translateRowsSequentially({
    rows: [],
    targetLanguage: 'English',
    translateRow: async (row) => {
      translateCalls += 1;
      return row;
    },
    onProgress: (progress) => {
      progressUpdates.push({ ...progress });
    },
  });

  assert.equal(translateCalls, 0);
  assert.deepEqual(progressUpdates, [
    { activeRowIndex: null, completed: 0, total: 0 },
  ]);
  assert.deepEqual(translatedRows, []);
});
