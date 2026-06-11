export type ResultStatusVariant = 'default' | 'success' | 'error';

export interface ResultStatusLabels {
  pass: string;
  fail: string;
  scoreOnly: string;
  error: string;
}

export interface ResultStatusBadge {
  variant: ResultStatusVariant;
  label: string;
}

const DEFAULT_RESULT_STATUS_LABELS: ResultStatusLabels = {
  pass: 'Pass',
  fail: 'Fail',
  scoreOnly: 'Score only',
  error: 'Error',
};

export function getResultStatusBadge(
  passed: boolean | null | undefined,
  error: string | null | undefined,
  labels: ResultStatusLabels = DEFAULT_RESULT_STATUS_LABELS,
): ResultStatusBadge {
  if (error) {
    return { variant: 'error', label: labels.error };
  }

  if (passed === true) {
    return { variant: 'success', label: labels.pass };
  }

  if (passed === false) {
    return { variant: 'error', label: labels.fail };
  }

  return { variant: 'default', label: labels.scoreOnly };
}
