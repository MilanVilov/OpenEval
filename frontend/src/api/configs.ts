import { apiFetch } from './client';
import type { EvalConfig, CreateConfigRequest } from '../types/config';

export function listConfigs(): Promise<EvalConfig[]> {
  return apiFetch('/configs');
}

export function getConfig(id: string): Promise<EvalConfig> {
  return apiFetch(`/configs/${id}`);
}

export function createConfig(data: CreateConfigRequest): Promise<EvalConfig> {
  return apiFetch('/configs', { method: 'POST', body: JSON.stringify(data) });
}

export function updateConfig(id: string, data: Partial<CreateConfigRequest>): Promise<EvalConfig> {
  return apiFetch(`/configs/${id}`, { method: 'PUT', body: JSON.stringify(data) });
}

export function deleteConfig(id: string): Promise<void> {
  return apiFetch(`/configs/${id}`, { method: 'DELETE' });
}
