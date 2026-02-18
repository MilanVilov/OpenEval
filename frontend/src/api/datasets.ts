import { apiFetch } from './client';
import type { Dataset, DatasetDetail } from '../types/dataset';

export function listDatasets(): Promise<Dataset[]> {
  return apiFetch('/datasets');
}

export function getDataset(id: string): Promise<DatasetDetail> {
  return apiFetch(`/datasets/${id}`);
}

export function uploadDataset(name: string, file: File): Promise<Dataset> {
  const form = new FormData();
  form.append('name', name);
  form.append('file', file);
  return apiFetch('/datasets', {
    method: 'POST',
    headers: {},
    body: form,
  });
}

export function deleteDataset(id: string): Promise<void> {
  return apiFetch(`/datasets/${id}`, { method: 'DELETE' });
}
