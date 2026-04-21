import { apiFetch } from './client';
import type {
  Schedule,
  ScheduleCreateRequest,
  ScheduleUpdateRequest,
} from '../types/schedule';

export function listSchedules(): Promise<Schedule[]> {
  return apiFetch('/schedules');
}

export function getSchedule(id: string): Promise<Schedule> {
  return apiFetch(`/schedules/${id}`);
}

export function createSchedule(data: ScheduleCreateRequest): Promise<Schedule> {
  return apiFetch('/schedules', { method: 'POST', body: JSON.stringify(data) });
}

export function updateSchedule(
  id: string,
  data: ScheduleUpdateRequest,
): Promise<Schedule> {
  return apiFetch(`/schedules/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export function toggleSchedule(id: string): Promise<Schedule> {
  return apiFetch(`/schedules/${id}/toggle`, { method: 'POST' });
}

export function runScheduleNow(id: string): Promise<Schedule> {
  return apiFetch(`/schedules/${id}/run-now`, { method: 'POST' });
}

export function deleteSchedule(id: string): Promise<void> {
  return apiFetch(`/schedules/${id}`, { method: 'DELETE' });
}
