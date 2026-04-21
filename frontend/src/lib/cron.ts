/**
 * Build a cron expression from preset fields.
 * Cron fields: minute hour day-of-month month day-of-week
 * - daily:   "M H * * *"
 * - weekly:  "M H * * D"  where D = comma-separated days (0=Sun ... 6=Sat)
 */
export function buildPresetCron(params: {
  mode: 'daily' | 'weekly';
  hour: number;
  minute: number;
  daysOfWeek?: number[];
}): string {
  const { mode, hour, minute, daysOfWeek } = params;
  if (mode === 'daily') {
    return `${minute} ${hour} * * *`;
  }
  const days = (daysOfWeek && daysOfWeek.length > 0 ? daysOfWeek : [1])
    .slice()
    .sort((a, b) => a - b)
    .join(',');
  return `${minute} ${hour} * * ${days}`;
}

/** Human-readable description of a cron expression. Best-effort. */
export function describeCron(expression: string): string {
  const parts = expression.trim().split(/\s+/);
  if (parts.length !== 5) return expression;
  const [minute, hour, dom, month, dow] = parts;
  const time = formatTime(hour, minute);

  if (dom === '*' && month === '*' && dow === '*') {
    return `Every day at ${time}`;
  }
  if (dom === '*' && month === '*' && dow !== '*') {
    return `Every ${formatDays(dow)} at ${time}`;
  }
  return expression;
}

const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

function formatDays(dow: string): string {
  const days = dow
    .split(',')
    .map((d) => parseInt(d, 10))
    .filter((d) => !Number.isNaN(d) && d >= 0 && d <= 6)
    .map((d) => DAY_NAMES[d]);
  if (days.length === 0) return dow;
  if (days.length === 1) return days[0];
  if (days.length === 2) return `${days[0]} and ${days[1]}`;
  return `${days.slice(0, -1).join(', ')}, and ${days[days.length - 1]}`;
}

function formatTime(hour: string, minute: string): string {
  const h = parseInt(hour, 10);
  const m = parseInt(minute, 10);
  if (Number.isNaN(h) || Number.isNaN(m)) return `${hour}:${minute}`;
  const hh = String(h).padStart(2, '0');
  const mm = String(m).padStart(2, '0');
  return `${hh}:${mm} UTC`;
}
