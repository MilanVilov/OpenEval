export type RemoteImportMode = 'create' | 'append';
export const REMOTE_PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

interface BasketSelection {
  selectionId: string;
}

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

export function countSelectedPageRows<T extends BasketSelection>(
  basket: T[],
  selectionIds: string[],
): number {
  if (basket.length === 0 || selectionIds.length === 0) {
    return 0;
  }

  const selectedIds = new Set(basket.map((item) => item.selectionId));
  return selectionIds.filter((selectionId) => selectedIds.has(selectionId)).length;
}

export function mergeBasketItems<T extends BasketSelection>(
  basket: T[],
  pageItems: T[],
): T[] {
  if (pageItems.length === 0) {
    return basket;
  }

  const merged = new Map(basket.map((item) => [item.selectionId, item]));
  pageItems.forEach((item) => {
    merged.set(item.selectionId, item);
  });
  return Array.from(merged.values());
}

export function removeBasketItems<T extends BasketSelection>(
  basket: T[],
  selectionIds: string[],
): T[] {
  if (basket.length === 0 || selectionIds.length === 0) {
    return basket;
  }

  const idsToRemove = new Set(selectionIds);
  return basket.filter((item) => !idsToRemove.has(item.selectionId));
}

export function parsePageSizeOverride(value: string): number | null {
  if (value === 'default') {
    return null;
  }

  const parsedValue = Number.parseInt(value, 10);
  if (!Number.isInteger(parsedValue) || parsedValue < 1) {
    return null;
  }
  return parsedValue;
}
