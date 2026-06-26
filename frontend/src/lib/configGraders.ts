import type { Grader } from '../types/config';

function hasText(value: string | undefined): boolean {
  return !!(value ?? '').trim();
}

function parseJsonSchema(grader: Grader): Record<string, unknown> {
  const graderName = grader.name.trim() || 'Unnamed';
  const schemaText = grader.schema_text?.trim();

  if (schemaText) {
    try {
      const parsed = JSON.parse(schemaText);
      if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
        throw new Error('Schema must be a JSON object');
      }
      return parsed as Record<string, unknown>;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Invalid JSON';
      throw new Error(`JSON schema grader "${graderName}" has invalid schema JSON: ${message}`);
    }
  }

  if (grader.schema && !Array.isArray(grader.schema)) {
    return grader.schema;
  }

  throw new Error(`JSON schema grader "${graderName}" requires a schema`);
}

function shouldSubmitGrader(grader: Grader): boolean {
  if (!grader.name.trim()) return false;

  const type = grader.type ?? 'prompt';
  if (type === 'prompt') return hasText(grader.prompt);
  if (type === 'string_check') {
    return hasText(grader.input_value) && hasText(grader.operation) && hasText(grader.reference_value);
  }
  if (type === 'python') return hasText(grader.source_code);
  if (type === 'json_schema') return hasText(grader.schema_text) || grader.schema !== undefined;
  if (type === 'json_field') return hasText(grader.field_name);

  return true;
}

export function buildGradersPayload(graders: Grader[]): Grader[] {
  return graders
    .filter(shouldSubmitGrader)
    .map((grader) => {
      const { schema: _schema, schema_text: _schemaText, ...rest } = grader;
      const schema = grader.type === 'json_schema'
        ? parseJsonSchema(grader)
        : undefined;
      return {
        ...rest,
        name: grader.name.trim(),
        model: grader.type === 'prompt' || grader.type === 'semantic_similarity'
          ? grader.model || undefined
          : undefined,
        ...(schema ? { schema } : {}),
        field_name: grader.type === 'json_field'
          ? (grader.field_name ?? '').trim() || undefined
          : undefined,
        threshold: grader.threshold,
        weight: grader.weight ?? 1,
      };
    });
}
