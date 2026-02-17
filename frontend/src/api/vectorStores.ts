import { apiFetch } from './client';
import type { VectorStore, CreateVectorStoreRequest } from '../types/vectorStore';

export function listVectorStores(): Promise<VectorStore[]> {
  return apiFetch('/vector-stores');
}

export function getVectorStore(id: string): Promise<VectorStore> {
  return apiFetch(`/vector-stores/${id}`);
}

export function createVectorStore(data: CreateVectorStoreRequest): Promise<VectorStore> {
  return apiFetch('/vector-stores', { method: 'POST', body: JSON.stringify(data) });
}

export function uploadFileToVectorStore(id: string, file: File): Promise<VectorStore> {
  const form = new FormData();
  form.append('file', file);
  return apiFetch(`/vector-stores/${id}/files`, {
    method: 'POST',
    headers: {},
    body: form,
  });
}

export function deleteVectorStore(id: string): Promise<void> {
  return apiFetch(`/vector-stores/${id}`, { method: 'DELETE' });
}
