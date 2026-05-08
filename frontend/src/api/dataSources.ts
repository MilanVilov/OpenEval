import { apiFetch } from './client';
import type {
  DataSource,
  DataSourceDetail,
  DataSourcePayload,
  ExploreDataSourceRequest,
  ExploreDataSourceResponse,
  ImportDatasetFromSourcePayload,
  ImportPreset,
  ImportPresetPayload,
} from '@/types/dataSource';
import type { Dataset, DatasetDetail } from '@/types/dataset';

export function listDataSources(): Promise<DataSource[]> {
  return apiFetch('/data-sources');
}

export function getDataSource(id: string): Promise<DataSourceDetail> {
  return apiFetch(`/data-sources/${id}`);
}

export function createDataSource(payload: DataSourcePayload): Promise<DataSource> {
  return apiFetch('/data-sources', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateDataSource(
  id: string,
  payload: Partial<DataSourcePayload>,
): Promise<DataSourceDetail> {
  return apiFetch(`/data-sources/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function deleteDataSource(id: string): Promise<void> {
  return apiFetch(`/data-sources/${id}`, { method: 'DELETE' });
}

export function listImportPresets(sourceId: string): Promise<ImportPreset[]> {
  return apiFetch(`/data-sources/${sourceId}/presets`);
}

export function createImportPreset(
  sourceId: string,
  payload: ImportPresetPayload,
): Promise<ImportPreset> {
  return apiFetch(`/data-sources/${sourceId}/presets`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateImportPreset(
  sourceId: string,
  presetId: string,
  payload: Partial<ImportPresetPayload>,
): Promise<ImportPreset> {
  return apiFetch(`/data-sources/${sourceId}/presets/${presetId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function deleteImportPreset(sourceId: string, presetId: string): Promise<void> {
  return apiFetch(`/data-sources/${sourceId}/presets/${presetId}`, { method: 'DELETE' });
}

export function exploreDataSource(
  sourceId: string,
  payload: ExploreDataSourceRequest,
): Promise<ExploreDataSourceResponse> {
  return apiFetch(`/data-sources/${sourceId}/explore`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function importDatasetFromSource(
  payload: ImportDatasetFromSourcePayload,
): Promise<Dataset> {
  return apiFetch('/datasets/import-from-source', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function appendDatasetFromSource(
  datasetId: string,
  selectedRecords: unknown[],
): Promise<DatasetDetail> {
  return apiFetch(`/datasets/${datasetId}/append-from-source`, {
    method: 'POST',
    body: JSON.stringify({ selected_records: selectedRecords }),
  });
}
