export type GraderType = 'prompt' | 'string_check' | 'python';

export type StringCheckOperation =
  | 'equals'
  | 'not_equals'
  | 'contains'
  | 'contains_ignore_case';

export interface CustomGrader {
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
  // shared
  threshold: number;
  weight?: number;
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
  comparer_type: string;
  comparer_config: Record<string, unknown>;
  custom_graders: CustomGrader[];
  comparer_weights: Record<string, number>;
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
  comparer_type: string;
  comparer_config: Record<string, unknown>;
  custom_graders?: CustomGrader[];
  comparer_weights?: Record<string, number>;
  tags?: string[];
  concurrency: number;
  readonly?: boolean;
  reasoning_config?: Record<string, string> | null;
  response_format?: Record<string, unknown> | null;
}
