import { apiFetch } from './client';
import type { EvalConfig, CreateConfigRequest } from '../types/config';
import { buildPaginationQuery } from './pagination';
import type { PaginatedResponse, PaginationParams } from '../types/pagination';

export interface ConfigPaginationParams extends PaginationParams {
  tags?: string[];
}

export function listConfigs(): Promise<EvalConfig[]> {
  return apiFetch('/configs');
}

export function listConfigsPage(
  params: ConfigPaginationParams,
): Promise<PaginatedResponse<EvalConfig>> {
  const query = new URLSearchParams(buildPaginationQuery(params).slice(1));
  params.tags?.forEach((tag) => query.append('tags', tag));
  return apiFetch(`/configs?${query.toString()}`);
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

export function duplicateConfig(id: string): Promise<EvalConfig> {
  return apiFetch(`/configs/${id}/duplicate`, { method: 'POST' });
}

export function deleteConfig(id: string): Promise<void> {
  return apiFetch(`/configs/${id}`, { method: 'DELETE' });
}

export function fetchAllTags(): Promise<string[]> {
  return apiFetch('/configs/tags');
}
