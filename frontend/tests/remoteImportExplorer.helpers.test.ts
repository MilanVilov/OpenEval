import assert from 'node:assert/strict';
import test from 'node:test';

import {
  countSelectedPageRows,
  mergeBasketItems,
  parsePageSizeOverride,
  removeBasketItems,
} from '../src/components/dataSources/remoteImportExplorer.helpers.ts';

interface BasketRow {
  selectionId: string;
  value: string;
}

test('parsePageSizeOverride returns null for source default and invalid values', () => {
  assert.equal(parsePageSizeOverride('default'), null);
  assert.equal(parsePageSizeOverride('100'), 100);
  assert.equal(parsePageSizeOverride('0'), null);
  assert.equal(parsePageSizeOverride('abc'), null);
});

test('countSelectedPageRows counts only rows present in the current page', () => {
  const basket: BasketRow[] = [
    { selectionId: 'page-1:0', value: 'first' },
    { selectionId: 'page-2:0', value: 'second' },
  ];

  assert.equal(countSelectedPageRows(basket, ['page-1:0', 'page-1:1']), 1);
  assert.equal(countSelectedPageRows(basket, ['page-3:0']), 0);
});

test('mergeBasketItems appends new page rows and refreshes existing selections', () => {
  const merged = mergeBasketItems<BasketRow>(
    [
      { selectionId: 'page-1:0', value: 'stale' },
      { selectionId: 'page-2:0', value: 'second' },
    ],
    [
      { selectionId: 'page-1:0', value: 'fresh' },
      { selectionId: 'page-1:1', value: 'third' },
    ],
  );

  assert.deepEqual(merged, [
    { selectionId: 'page-1:0', value: 'fresh' },
    { selectionId: 'page-2:0', value: 'second' },
    { selectionId: 'page-1:1', value: 'third' },
  ]);
});

test('removeBasketItems drops every selected row from the current page', () => {
  const remaining = removeBasketItems<BasketRow>(
    [
      { selectionId: 'page-1:0', value: 'first' },
      { selectionId: 'page-1:1', value: 'second' },
      { selectionId: 'page-2:0', value: 'third' },
    ],
    ['page-1:0', 'page-1:1'],
  );

  assert.deepEqual(remaining, [
    { selectionId: 'page-2:0', value: 'third' },
  ]);
});
