export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonObject | JsonArray;

export interface JsonObject {
  [key: string]: JsonValue;
}

export type JsonArray = JsonValue[];

export interface DataSource {
  id: string;
  name: string;
  url: string;
  method: string;
  auth_type: string;
  pagination_mode: string;
  has_secret_credentials: boolean;
  secret_header_names: string[];
  created_at: string;
  updated_at: string;
}

export interface DataSourceDetail extends DataSource {
  query_params: Record<string, string>;
  request_body: JsonValue | null;
  headers: Record<string, string>;
  pagination_config: Record<string, JsonValue>;
}

export interface DataSourcePayload {
  name: string;
  url: string;
  method: 'GET' | 'POST';
  auth_type: 'none' | 'bearer' | 'basic' | 'header_set';
  query_params: Record<string, string>;
  request_body: JsonValue | null;
  headers: Record<string, string>;
  pagination_mode: 'none' | 'page' | 'offset' | 'next_token';
  pagination_config: Record<string, JsonValue>;
  bearer_token?: string;
  basic_username?: string;
  basic_password?: string;
  secret_headers?: Record<string, string>;
}

export interface ImportPreset {
  id: string;
  data_source_id: string;
  name: string;
  records_path: string;
  field_mapping: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export interface ImportPresetPayload {
  name: string;
  records_path: string;
  field_mapping: Record<string, string>;
}

export interface ExploreDataSourceRequest {
  preset_id?: string;
  records_path?: string;
  field_mapping?: Record<string, string>;
  page_state?: Record<string, JsonValue>;
}

export interface ExploreDataSourceResponse {
  request_summary: Record<string, JsonValue>;
  raw_response: JsonValue;
  candidate_array_paths: string[];
  field_candidates: string[];
  records: JsonValue[];
  mapped_rows: Record<string, string>[];
  current_page_state: Record<string, JsonValue> | null;
  next_page_state: Record<string, JsonValue> | null;
  previous_page_state: Record<string, JsonValue> | null;
}

export interface ImportDatasetFromSourcePayload {
  name: string;
  selected_records: unknown[];
  preset_id?: string;
  data_source_id?: string;
  records_path?: string;
  field_mapping?: Record<string, string>;
}

export interface ImportSourceSnapshot {
  data_source_id: string;
  records_path: string;
  field_mapping: Record<string, string>;
}
