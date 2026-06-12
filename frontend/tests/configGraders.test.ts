import assert from 'node:assert/strict';
import test from 'node:test';

import { buildGradersPayload } from '../src/lib/configGraders.ts';
import type { Grader } from '../src/types/config.ts';

test('buildGradersPayload preserves a blank threshold as null', () => {
  const graders: Grader[] = [
    {
      name: ' judge ',
      type: 'prompt',
      prompt: 'Score this',
      threshold: null,
      weight: 1,
    },
  ];

  assert.deepEqual(buildGradersPayload(graders), [
    {
      name: 'judge',
      type: 'prompt',
      prompt: 'Score this',
      threshold: null,
      weight: 1,
      model: undefined,
      field_name: undefined,
    },
  ]);
});

test('buildGradersPayload keeps numeric thresholds unchanged', () => {
  const graders: Grader[] = [
    {
      name: 'schema',
      type: 'json_schema',
      strict: true,
      threshold: 1,
      weight: 0.5,
    },
  ];

  assert.equal(buildGradersPayload(graders)[0].threshold, 1);
});
