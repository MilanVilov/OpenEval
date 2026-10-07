import assert from 'node:assert/strict';
import test from 'node:test';

import { decisionQuestionExample, parseDecisionConfig } from '../src/lib/decisionConfig.ts';

test('all Decisions examples parse into API question configuration', () => {
  for (const type of ['predicate', 'choice', 'score'] as const) {
    const config = parseDecisionConfig(decisionQuestionExample(type));
    assert.equal(config.questions[0].type, type);
    assert.ok(config.questions[0].name);
    assert.ok(config.questions[0].instructions);
  }
});

test('invalid JSON and unnamed, duplicated, or incomplete questions are rejected', () => {
  for (const source of ['{', '{}', '[]', '[{}]', '[{"type":"text"}]',
    '[{"type":"choice","name":"team","instructions":"Pick"}]',
    '[{"type":"score","name":"score","instructions":"Rate","levels":[]}]',
  ]) {
    assert.throws(() => parseDecisionConfig(source));
  }
  const { questions } = parseDecisionConfig(decisionQuestionExample('predicate'));
  assert.throws(() => parseDecisionConfig(JSON.stringify([...questions, ...questions])), /unique/);
});
