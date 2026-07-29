import assert from 'node:assert/strict';
import test from 'node:test';

import { hasClampedOverflow } from '../src/lib/expandableCell.ts';

test('hasClampedOverflow detects content taller than its visible height', () => {
  assert.equal(hasClampedOverflow({ clientHeight: 80, scrollHeight: 120 }), true);
});

test('hasClampedOverflow ignores equal heights and subpixel rounding', () => {
  assert.equal(hasClampedOverflow({ clientHeight: 80, scrollHeight: 80 }), false);
  assert.equal(hasClampedOverflow({ clientHeight: 80, scrollHeight: 81 }), false);
});
