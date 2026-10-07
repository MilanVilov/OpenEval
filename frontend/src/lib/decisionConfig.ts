import type { DecisionConfig } from '../types/config';

export type DecisionQuestionType = 'predicate' | 'choice' | 'score';

export function decisionQuestionExample(type: DecisionQuestionType): string {
  const question: Record<string, unknown> = {
    type, name: 'decision', instructions: 'Does this input need follow-up?',
  };
  if (type === 'choice') {
    question.instructions = 'Which team should handle this request?';
    question.choices = [
      { value: 'billing', description: 'Payments, invoices, and refunds.' },
      { value: 'support', description: 'Problems using the product.' },
    ];
  }
  if (type === 'score') {
    question.instructions = 'How severe is this issue?';
    question.levels = [
      { label: 'Low', description: 'Appearance only; no lost functionality.' },
      { label: 'High', description: 'A task fails with no workaround.' },
    ];
  }
  return JSON.stringify([question], null, 2);
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function parseDecisionConfig(source: string): DecisionConfig {
  let questions: unknown;
  try {
    questions = JSON.parse(source);
  } catch {
    throw new Error('Decision questions must be valid JSON.');
  }
  if (!Array.isArray(questions) || questions.length === 0 || !questions.every(isObject)) {
    throw new Error('Provide a JSON array containing at least one decision question.');
  }
  const names = new Set<string>();
  for (const question of questions) {
    if (typeof question.name !== 'string' || !question.name.trim()
      || typeof question.instructions !== 'string' || !question.instructions.trim()) {
      throw new Error('Each question needs a name and instructions.');
    }
    if (names.has(question.name)) throw new Error('Decision question names must be unique.');
    names.add(question.name);
    if (!['predicate', 'choice', 'score'].includes(String(question.type))) {
      throw new Error('Question type must be predicate, choice, or score.');
    }
    if (question.type === 'choice' && (!Array.isArray(question.choices) || question.choices.length < 2)) {
      throw new Error('Choice questions need at least two string or boolean values.');
    }
    if (question.type === 'score' && (!Array.isArray(question.levels) || question.levels.length < 2)) {
      throw new Error('Score questions need at least two ordered levels with labels.');
    }
  }
  return { questions };
}
