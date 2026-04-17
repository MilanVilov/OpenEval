export type GraderType = 'prompt' | 'string_check' | 'python' | 'semantic_similarity' | 'json_schema' | 'json_field';

export type StringCheckOperation =
  | 'equals'
  | 'not_equals'
  | 'contains'
  | 'contains_ignore_case';

export interface Grader {
  name: string;
  type: GraderType;
  // prompt grader
  prompt?: string;
  model?: string;
  // string check grader
  input_value?: string;
  operation?: StringCheckOperation;
  reference_value?: string;
  // python grader
  source_code?: string;
  // semantic similarity
  // uses model (above) and threshold (below)
  // json schema
  strict?: boolean;
  // json field
  field_name?: string;
  case_sensitive?: boolean;
  strip_whitespace?: boolean;
  // shared
  threshold: number;
  weight: number;
}

export interface EvalConfig {
  id: string;
  name: string;
  system_prompt: string;
  model: string;
  temperature: number;
  max_tokens: number | null;
  tools: string[];
  tool_options: Record<string, unknown>;
  graders: Grader[];
  tags: string[];
  concurrency: number;
  readonly: boolean;
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
  graders?: Grader[];
  tags?: string[];
  concurrency: number;
  readonly?: boolean;
  reasoning_config?: Record<string, string> | null;
  response_format?: Record<string, unknown> | null;
}
