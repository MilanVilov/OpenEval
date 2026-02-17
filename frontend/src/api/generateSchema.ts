import { apiFetch } from './client';

interface GenerateSchemaRequest {
  description: string;
}

interface GenerateSchemaResponse {
  schema_name: string;
  schema_body: Record<string, unknown>;
}

export async function generateSchema(description: string): Promise<GenerateSchemaResponse> {
  return apiFetch<GenerateSchemaResponse>('/generate-schema', {
    method: 'POST',
    body: JSON.stringify({ description } satisfies GenerateSchemaRequest),
  });
}
