export interface Dataset {
  id: string;
  name: string;
  file_path: string;
  row_count: number;
  columns: string[];
  created_at: string;
}

export interface DatasetDetail extends Dataset {
  rows: Record<string, string>[];
}
