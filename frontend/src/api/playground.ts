import { apiFetch } from './client';

export interface PlaygroundRequest {
  config_id: string;
  message: string;
}

export interface PlaygroundResponse {
  text: string;
  latency_ms: number;
  token_usage: { input_tokens: number; output_tokens: number };
  raw_response: Record<string, unknown>;
}

export function runPlayground(data: PlaygroundRequest): Promise<PlaygroundResponse> {
  return apiFetch('/playground', { method: 'POST', body: JSON.stringify(data) });
}
