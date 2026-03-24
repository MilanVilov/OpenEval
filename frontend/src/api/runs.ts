import { apiFetch, downloadFile } from './client';
import type { EvalRun, EvalResult, RunProgress, CreateRunRequest } from '../types/run';

export function listRuns(): Promise<EvalRun[]> {
  return apiFetch('/runs');
}

export function getRun(id: string): Promise<EvalRun> {
  return apiFetch(`/runs/${id}`);
}

export function createRun(data: CreateRunRequest): Promise<EvalRun> {
  return apiFetch('/runs', { method: 'POST', body: JSON.stringify(data) });
}

export function getRunProgress(id: string): Promise<RunProgress> {
  return apiFetch(`/runs/${id}/progress`);
}

export function getRunResults(id: string, failedOnly: boolean = false): Promise<EvalResult[]> {
  const params = failedOnly ? '?failed_only=true' : '';
  return apiFetch(`/runs/${id}/results${params}`);
}

export function deleteRun(id: string): Promise<void> {
  return apiFetch(`/runs/${id}`, { method: 'DELETE' });
}

export function compareRuns(runA: string, runB: string): Promise<{ run_a: EvalRun | null; run_b: EvalRun | null; results_a: EvalResult[]; results_b: EvalResult[] }> {
  return apiFetch(`/runs/compare?run_a=${runA}&run_b=${runB}`);
}

export function exportRun(id: string): Promise<void> {
  return downloadFile(`/runs/${id}/export`);
}
