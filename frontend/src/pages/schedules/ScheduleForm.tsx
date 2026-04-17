import { useState, useEffect, type FormEvent } from 'react';
import { listConfigs } from '@/api/configs';
import { listDatasets } from '@/api/datasets';
import type { EvalConfig } from '@/types/config';
import type { Dataset } from '@/types/dataset';
import type { Schedule, ScheduleFormData } from '@/types/schedule';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Spinner } from '@/components/Spinner';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { buildPresetCron, describeCron } from '@/lib/cron';

type Mode = 'daily' | 'weekly' | 'advanced';

interface ScheduleFormProps {
  initial?: Schedule;
  submitLabel: string;
  onSubmit: (data: ScheduleFormData) => Promise<void>;
  onCancel: () => void;
}

const DAY_LABELS: Array<[number, string]> = [
  [1, 'Mon'], [2, 'Tue'], [3, 'Wed'], [4, 'Thu'],
  [5, 'Fri'], [6, 'Sat'], [0, 'Sun'],
];

export function ScheduleForm({ initial, submitLabel, onSubmit, onCancel }: ScheduleFormProps) {
  const [configs, setConfigs] = useState<EvalConfig[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loadingRefs, setLoadingRefs] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState(initial?.name ?? '');
  const [configId, setConfigId] = useState(initial?.eval_config_id ?? '');
  const [datasetId, setDatasetId] = useState(initial?.dataset_id ?? '');
  const [enabled, setEnabled] = useState(initial?.enabled ?? true);
  const [slackUrl, setSlackUrl] = useState('');
  const [minAccuracyPct, setMinAccuracyPct] = useState<string>(
    initial?.min_accuracy != null ? String(Math.round(initial.min_accuracy * 100)) : '',
  );

  const [mode, setMode] = useState<Mode>(detectMode(initial?.cron_expression));
  const [hour, setHour] = useState<number>(initial ? extractHour(initial.cron_expression) : 9);
  const [minute, setMinute] = useState<number>(initial ? extractMinute(initial.cron_expression) : 0);
  const [daysOfWeek, setDaysOfWeek] = useState<number[]>(
    initial ? extractDays(initial.cron_expression) : [1],
  );
  const [cronExpr, setCronExpr] = useState(initial?.cron_expression ?? '0 9 * * *');

  useEffect(() => {
    Promise.all([listConfigs(), listDatasets()])
      .then(([c, d]) => {
        setConfigs(c);
        setDatasets(d);
        if (!initial && c.length > 0 && !configId) setConfigId(c[0].id);
        if (!initial && d.length > 0 && !datasetId) setDatasetId(d[0].id);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoadingRefs(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const effectiveCron =
    mode === 'advanced'
      ? cronExpr.trim()
      : buildPresetCron({ mode, hour, minute, daysOfWeek });

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!name.trim() || !configId || !datasetId || !effectiveCron) {
      setError('Name, config, dataset, and schedule are required.');
      return;
    }

    let minAccuracy: number | null = null;
    if (minAccuracyPct.trim()) {
      const v = Number(minAccuracyPct);
      if (Number.isNaN(v) || v < 0 || v > 100) {
        setError('Minimum accuracy must be between 0 and 100.');
        return;
      }
      minAccuracy = v / 100;
    }

    setSubmitting(true);
    try {
      await onSubmit({
        name: name.trim(),
        eval_config_id: configId,
        dataset_id: datasetId,
        cron_expression: effectiveCron,
        enabled,
        ...(buildWebhookField({
          hasExistingWebhook: initial?.has_slack_webhook ?? false,
          value: slackUrl,
        })),
        min_accuracy: minAccuracy,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save schedule.');
    } finally {
      setSubmitting(false);
    }
  }

  function toggleDay(day: number) {
    setDaysOfWeek((prev) =>
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day],
    );
  }

  if (loadingRefs) return <LoadingSkeleton rows={4} />;

  return (
    <form onSubmit={handleSubmit} className="space-y-5 max-w-[720px]">
      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      <div className="space-y-2">
        <Label htmlFor="sched-name">Name</Label>
        <Input id="sched-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Nightly regression" />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label>Config</Label>
          <Select value={configId} onChange={(e) => setConfigId(e.target.value)} disabled={configs.length === 0}>
            <option value="" disabled>Select a config…</option>
            {configs.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Dataset</Label>
          <Select value={datasetId} onChange={(e) => setDatasetId(e.target.value)} disabled={datasets.length === 0}>
            <option value="" disabled>Select a dataset…</option>
            {datasets.map((d) => <option key={d.id} value={d.id}>{d.name} ({d.row_count} rows)</option>)}
          </Select>
        </div>
      </div>

      <div className="space-y-2">
        <Label>Schedule (UTC)</Label>
        <div className="flex gap-2">
          {(['daily', 'weekly', 'advanced'] as Mode[]).map((m) => (
            <Button
              key={m}
              type="button"
              size="sm"
              variant={mode === m ? 'default' : 'outline'}
              onClick={() => setMode(m)}
            >
              {m === 'advanced' ? 'Advanced (cron)' : m.charAt(0).toUpperCase() + m.slice(1)}
            </Button>
          ))}
        </div>

        {mode !== 'advanced' && (
          <div className="flex items-center gap-2 pt-2">
            <Label className="text-sm text-foreground-secondary">At</Label>
            <Input
              type="number" min={0} max={23}
              className="w-20 tabular-nums"
              value={hour}
              onChange={(e) => setHour(clamp(parseInt(e.target.value, 10) || 0, 0, 23))}
            />
            <span className="text-foreground-secondary">:</span>
            <Input
              type="number" min={0} max={59}
              className="w-20 tabular-nums"
              value={minute}
              onChange={(e) => setMinute(clamp(parseInt(e.target.value, 10) || 0, 0, 59))}
            />
            <span className="text-sm text-foreground-secondary">UTC</span>
          </div>
        )}

        {mode === 'weekly' && (
          <div className="flex flex-wrap gap-2 pt-2">
            {DAY_LABELS.map(([day, label]) => (
              <Button
                key={day}
                type="button"
                size="sm"
                variant={daysOfWeek.includes(day) ? 'default' : 'outline'}
                onClick={() => toggleDay(day)}
              >
                {label}
              </Button>
            ))}
          </div>
        )}

        {mode === 'advanced' && (
          <Input
            className="font-mono"
            value={cronExpr}
            onChange={(e) => setCronExpr(e.target.value)}
            placeholder="*/15 * * * *"
          />
        )}

        <p className="text-xs text-foreground-secondary pt-1">
          Expression: <code className="font-mono">{effectiveCron}</code> — {describeCron(effectiveCron)}
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="sched-slack">Slack webhook URL (optional override)</Label>
        <Input
          id="sched-slack"
          value={slackUrl}
          onChange={(e) => setSlackUrl(e.target.value)}
          placeholder={getWebhookPlaceholder(initial)}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="sched-min-acc">Alert below accuracy (%) — optional</Label>
        <Input
          id="sched-min-acc"
          type="number" min={0} max={100}
          value={minAccuracyPct}
          onChange={(e) => setMinAccuracyPct(e.target.value)}
          placeholder="e.g. 80"
          className="w-40 tabular-nums"
        />
      </div>

      <div className="flex items-center gap-2">
        <input
          id="sched-enabled"
          type="checkbox"
          checked={enabled}
          onChange={(e) => setEnabled(e.target.checked)}
          className="h-4 w-4"
        />
        <Label htmlFor="sched-enabled" className="cursor-pointer">Enabled</Label>
      </div>

      <div className="flex justify-end gap-2 pt-4">
        <Button type="button" variant="outline" onClick={onCancel}>Cancel</Button>
        <Button type="submit" disabled={submitting}>
          {submitting && <Spinner className="mr-2" />}
          {submitting ? 'Saving…' : submitLabel}
        </Button>
      </div>
    </form>
  );
}

function clamp(n: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, n));
}

function detectMode(expr: string | undefined): Mode {
  if (!expr) return 'daily';
  const parts = expr.trim().split(/\s+/);
  if (parts.length !== 5) return 'advanced';
  const [minute, hour, dom, month, dow] = parts;
  if (!isPlainCronInteger(minute, 0, 59) || !isPlainCronInteger(hour, 0, 23)) {
    return 'advanced';
  }
  if (dom === '*' && month === '*' && dow === '*') return 'daily';
  if (dom === '*' && month === '*' && /^[0-6](,[0-6])*$/.test(dow)) return 'weekly';
  return 'advanced';
}

function isPlainCronInteger(value: string, min: number, max: number): boolean {
  if (!/^\d+$/.test(value)) return false;
  const parsed = parseInt(value, 10);
  return parsed >= min && parsed <= max;
}

function extractHour(expr: string): number {
  const parts = expr.trim().split(/\s+/);
  const h = parseInt(parts[1] ?? '0', 10);
  return Number.isNaN(h) ? 9 : h;
}

function extractMinute(expr: string): number {
  const parts = expr.trim().split(/\s+/);
  const m = parseInt(parts[0] ?? '0', 10);
  return Number.isNaN(m) ? 0 : m;
}

function extractDays(expr: string): number[] {
  const parts = expr.trim().split(/\s+/);
  const dow = parts[4] ?? '1';
  if (dow === '*') return [1];
  return dow
    .split(',')
    .map((d) => parseInt(d, 10))
    .filter((d) => !Number.isNaN(d) && d >= 0 && d <= 6);
}

function buildWebhookField(params: {
  hasExistingWebhook: boolean;
  value: string;
}): Pick<ScheduleFormData, 'slack_webhook_url'> | Record<string, never> {
  const normalized = params.value.trim();
  if (normalized) {
    return { slack_webhook_url: normalized };
  }
  if (!params.hasExistingWebhook) {
    return { slack_webhook_url: null };
  }
  return {};
}

function getWebhookPlaceholder(initial: Schedule | undefined): string {
  if (initial?.has_slack_webhook) {
    return 'Leave blank to keep the saved Slack webhook';
  }
  return 'Uses SLACK_WEBHOOK_URL env if empty';
}
