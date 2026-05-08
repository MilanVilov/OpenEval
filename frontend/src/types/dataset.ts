import type { ImportSourceSnapshot } from './dataSource';

export interface Dataset {
  id: string;
  name: string;
  file_path: string;
  row_count: number;
  columns: string[];
  import_preset_id: string | null;
  has_import_source: boolean;
  created_at: string;
}

export interface DatasetDetail extends Dataset {
  import_source_snapshot: ImportSourceSnapshot | null;
  rows: Record<string, string>[];
}
