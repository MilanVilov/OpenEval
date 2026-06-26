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
      schema: { type: 'object' },
      threshold: 1,
      weight: 0.5,
    },
  ];

  assert.equal(buildGradersPayload(graders)[0].threshold, 1);
});

test('buildGradersPayload parses json schema text into a schema object', () => {
  const graders: Grader[] = [
    {
      name: 'shape',
      type: 'json_schema',
      schema_text: '{"type":"object","properties":{"answer":{"type":"string"}}}',
      threshold: 1,
      weight: 1,
    },
  ];

  assert.deepEqual(buildGradersPayload(graders)[0].schema, {
    type: 'object',
    properties: {
      answer: { type: 'string' },
    },
  });
});

test('buildGradersPayload rejects invalid json schema text', () => {
  const graders: Grader[] = [
    {
      name: 'shape',
      type: 'json_schema',
      schema_text: '{"type":"object"',
      threshold: 1,
      weight: 1,
    },
  ];

  assert.throws(
    () => buildGradersPayload(graders),
    /JSON schema grader "shape" has invalid schema JSON/,
  );
});
