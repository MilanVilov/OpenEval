export interface EvalRun {
  id: string;
  eval_config_id: string;
  dataset_id: string;
  status: string;
  progress: number;
  total_rows: number;
  summary: RunSummary | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  config_name: string | null;
  dataset_name: string | null;
}

export interface RunSummary {
  total: number;
  passed: number;
  failed: number;
  errors: number;
  accuracy: number;
  avg_latency_ms: number;
  avg_score: number;
  avg_input_tokens: number;
  avg_output_tokens: number;
}

export interface RunProgress {
  status: string;
  progress: number;
  total_rows: number;
  summary: RunSummary | null;
}

export interface EvalResult {
  id: string;
  eval_run_id: string;
  row_index: number;
  input_data: string;
  expected_output: string;
  actual_output: string | null;
  comparer_score: number | null;
  comparer_details: Record<string, unknown> | null;
  passed: boolean | null;
  latency_ms: number | null;
  token_usage: { input_tokens: number; output_tokens: number } | null;
  error: string | null;
  created_at: string;
}

export interface CreateRunRequest {
  eval_config_id: string;
  dataset_id: string;
}
