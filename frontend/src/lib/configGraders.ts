import type { Grader } from '../types/config';

function hasText(value: string | undefined): boolean {
  return !!(value ?? '').trim();
}

function shouldSubmitGrader(grader: Grader): boolean {
  if (!grader.name.trim()) return false;

  const type = grader.type ?? 'prompt';
  if (type === 'prompt') return hasText(grader.prompt);
  if (type === 'string_check') {
    return hasText(grader.input_value) && hasText(grader.operation) && hasText(grader.reference_value);
  }
  if (type === 'python') return hasText(grader.source_code);
  if (type === 'json_field') return hasText(grader.field_name);

  return true;
}

export function buildGradersPayload(graders: Grader[]): Grader[] {
  return graders
    .filter(shouldSubmitGrader)
    .map((grader) => ({
      ...grader,
      name: grader.name.trim(),
      model: grader.type === 'prompt' || grader.type === 'semantic_similarity'
        ? grader.model || undefined
        : undefined,
      field_name: grader.type === 'json_field'
        ? (grader.field_name ?? '').trim() || undefined
        : undefined,
      threshold: grader.threshold,
      weight: grader.weight ?? 1,
    }));
}
