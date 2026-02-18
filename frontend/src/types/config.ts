export interface EvalConfig {
  id: string;
  name: string;
  system_prompt: string;
  model: string;
  temperature: number;
  max_tokens: number | null;
  tools: string[];
  tool_options: Record<string, unknown>;
  comparer_type: string;
  comparer_config: Record<string, unknown>;
  concurrency: number;
  reasoning_config: Record<string, string> | null;
  response_format: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface CreateConfigRequest {
  name: string;
  system_prompt: string;
  model: string;
  temperature: number;
  max_tokens?: number | null;
  tools: string[];
  tool_options: Record<string, unknown>;
  comparer_type: string;
  comparer_config: Record<string, unknown>;
  concurrency: number;
  reasoning_config?: Record<string, string> | null;
  response_format?: Record<string, unknown> | null;
}
