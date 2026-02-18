import { apiFetch } from './client';
import type { EvalRun } from '../types/run';

interface DashboardData {
  recent_runs: EvalRun[];
}

export function getDashboard(): Promise<DashboardData> {
  return apiFetch('/dashboard');
}
