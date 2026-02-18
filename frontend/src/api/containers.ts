import { apiFetch } from './client';
import type { Container, CreateContainerRequest } from '../types/container';

export function listContainers(): Promise<Container[]> {
  return apiFetch('/containers');
}

export function getContainer(id: string): Promise<Container> {
  return apiFetch(`/containers/${id}`);
}

export function createContainer(data: CreateContainerRequest): Promise<Container> {
  return apiFetch('/containers', { method: 'POST', body: JSON.stringify(data) });
}

export function uploadFileToContainer(id: string, file: File): Promise<Container> {
  const form = new FormData();
  form.append('file', file);
  return apiFetch(`/containers/${id}/files`, {
    method: 'POST',
    headers: {},
    body: form,
  });
}

export function deleteContainer(id: string): Promise<void> {
  return apiFetch(`/containers/${id}`, { method: 'DELETE' });
}
