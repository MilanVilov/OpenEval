export interface LastRunSummary {
  id: string;
  status: string;
  accuracy: number | null;
  completed_at: string | null;
}

export interface Schedule {
  id: string;
  name: string;
  eval_config_id: string;
  dataset_id: string;
  cron_expression: string;
  enabled: boolean;
  slack_webhook_url: string | null;
  min_accuracy: number | null;
  last_triggered_at: string | null;
  next_run_at: string | null;
  created_at: string;
  updated_at: string;
  config_name: string | null;
  dataset_name: string | null;
  last_run: LastRunSummary | null;
}

export interface ScheduleCreateRequest {
  name: string;
  eval_config_id: string;
  dataset_id: string;
  cron_expression: string;
  enabled: boolean;
  slack_webhook_url: string | null;
  min_accuracy: number | null;
}

export type ScheduleUpdateRequest = Partial<ScheduleCreateRequest>;
