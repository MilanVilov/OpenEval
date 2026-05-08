export type RemoteImportMode = 'create' | 'append';

export function splitInitialFieldMapping(fieldMapping?: Record<string, string>): {
  input: string;
  expectedOutput: string;
} {
  const input = fieldMapping?.input ?? '';
  const expectedOutput = fieldMapping?.expected_output ?? '';

  return {
    input,
    expectedOutput,
  };
}

export function buildDraftFieldMapping({
  mode,
  inputTemplate,
  expectedOutputTemplate,
  lockedFieldMapping,
}: {
  mode: RemoteImportMode;
  inputTemplate: string;
  expectedOutputTemplate: string;
  lockedFieldMapping?: Record<string, string>;
}): {
  fieldMapping: Record<string, string> | null;
  error: string | null;
} {
  if (mode === 'append') {
    return {
      fieldMapping: lockedFieldMapping ?? null,
      error: lockedFieldMapping ? null : 'Locked dataset mapping is missing',
    };
  }

  const input = inputTemplate.trim();
  const expectedOutput = expectedOutputTemplate.trim();
  if (!input && !expectedOutput) {
    return { fieldMapping: null, error: null };
  }
  if (!input || !expectedOutput) {
    return {
      fieldMapping: null,
      error: 'Both input and expected_output mappings are required',
    };
  }

  return {
    fieldMapping: {
      input,
      expected_output: expectedOutput,
    },
    error: null,
  };
}

export function buildDisabledReason({
  mode,
  basketCount,
  datasetName,
  recordsPath,
  hasMapping,
}: {
  mode: RemoteImportMode;
  basketCount: number;
  datasetName: string;
  recordsPath: string;
  hasMapping: boolean;
}): string {
  if (basketCount === 0) {
    return 'Add rows from the mapped preview into the basket.';
  }
  if (mode === 'create' && !datasetName.trim()) {
    return 'Enter a dataset name in the basket section.';
  }
  if (!recordsPath.trim()) {
    return 'Choose the records path before creating the dataset.';
  }
  if (!hasMapping) {
    return 'Define input and expected_output mappings, then click Show Mapped Data.';
  }
  return '';
}
