import { useState } from 'react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Textarea } from '@/components/ui/textarea';
import {
  appendDatasetFromSource,
  exploreDataSource,
  importDatasetFromSource,
} from '@/api/dataSources';
import { JsonTreeView } from '@/components/JsonTreeView';
import { Spinner } from '@/components/Spinner';
import type {
  ExploreDataSourceRequest,
  ExploreDataSourceResponse,
  JsonValue,
} from '@/types/dataSource';
import { ArrowLeft, ArrowRight, Download, Trash2 } from 'lucide-react';

interface RemoteImportExplorerProps {
  sourceId: string;
  mode: 'create' | 'append';
  presetId?: string;
  selectedPresetName?: string;
  recordsPath?: string;
  fieldMapping?: Record<string, string>;
  datasetId?: string;
  defaultDatasetName?: string;
  savingMapping?: boolean;
  saveMappingError?: string | null;
  onSaveMapping?: (payload: {
    name: string;
    records_path: string;
    field_mapping: Record<string, string>;
  }) => Promise<void> | void;
  onComplete: (datasetId: string) => void;
}

interface BasketItem {
  selectionId: string;
  record: JsonValue;
  mappedRow: Record<string, string>;
}

export function RemoteImportExplorer({
  sourceId,
  mode,
  presetId,
  selectedPresetName,
  recordsPath,
  fieldMapping,
  datasetId,
  defaultDatasetName,
  savingMapping = false,
  saveMappingError,
  onSaveMapping,
  onComplete,
}: RemoteImportExplorerProps) {
  const initialMapping = splitInitialFieldMapping(fieldMapping);
  const [datasetName, setDatasetName] = useState(defaultDatasetName ?? '');
  const [mappingName, setMappingName] = useState(selectedPresetName ?? '');
  const [draftRecordsPath, setDraftRecordsPath] = useState(recordsPath ?? '');
  const [inputTemplate, setInputTemplate] = useState(initialMapping.input);
  const [expectedOutputTemplate, setExpectedOutputTemplate] = useState(initialMapping.expectedOutput);
  const [basket, setBasket] = useState<BasketItem[]>([]);
  const [exploreResult, setExploreResult] = useState<ExploreDataSourceResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeRecordsPath = (recordsPath ?? draftRecordsPath).trim();
  const mappingResult = buildDraftFieldMapping({
    mode,
    inputTemplate,
    expectedOutputTemplate,
    lockedFieldMapping: fieldMapping,
  });
  const currentRecords = exploreResult?.records ?? [];
  const currentMappedRows = exploreResult?.mapped_rows ?? [];
  const selectionScope = JSON.stringify({
    pageState: exploreResult?.current_page_state ?? { page: 'root' },
    recordsPath: activeRecordsPath || '$',
    mapping: mappingResult.fieldMapping ?? null,
  });
  const canCreateDataset = mode === 'append'
    ? basket.length > 0
    : basket.length > 0
        && Boolean(datasetName.trim())
        && Boolean(activeRecordsPath)
        && mappingResult.fieldMapping !== null;

  async function handleExplore(
    pageState?: Record<string, JsonValue> | null,
    overrideRecordsPath?: string,
  ) {
    if (mappingResult.error) {
      setError(mappingResult.error);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const nextRecordsPath = (overrideRecordsPath ?? activeRecordsPath).trim();
      const payload: ExploreDataSourceRequest = {
        page_state: pageState ?? undefined,
        records_path: nextRecordsPath || undefined,
      };
      if (mappingResult.fieldMapping) {
        payload.field_mapping = mappingResult.fieldMapping;
      }
      const result = await exploreDataSource(sourceId, payload);
      setExploreResult(result);
    } catch (exploreError) {
      setError(exploreError instanceof Error ? exploreError.message : 'Failed to explore data source');
    } finally {
      setLoading(false);
    }
  }

  async function handleShowMappedData() {
    if (!exploreResult) {
      setError('Explore the response first so you can choose the records path for the current page.');
      return;
    }
    if (!activeRecordsPath) {
      setError('Choose the records path before showing mapped data.');
      return;
    }
    if (mappingResult.error || mappingResult.fieldMapping === null) {
      setError(mappingResult.error ?? 'Define a valid mapping before showing mapped data.');
      return;
    }
    await handleExplore(exploreResult.current_page_state);
  }

  async function handleSelectRecordsPath(path: string) {
    setDraftRecordsPath(path);
    await handleExplore(exploreResult?.current_page_state, path);
  }

  async function handleSaveMapping() {
    if (!onSaveMapping) {
      return;
    }
    if (!mappingName.trim()) {
      setError('Enter a name before saving the mapping.');
      return;
    }
    if (!activeRecordsPath) {
      setError('Choose the records path before saving the mapping.');
      return;
    }
    if (mappingResult.error || mappingResult.fieldMapping === null) {
      setError(mappingResult.error ?? 'Define a valid mapping before saving.');
      return;
    }

    setError(null);
    await onSaveMapping({
      name: mappingName.trim(),
      records_path: activeRecordsPath,
      field_mapping: mappingResult.fieldMapping,
    });
  }

  function toggleSelection(rowIndex: number) {
    if (!currentMappedRows[rowIndex] || currentRecords[rowIndex] === undefined) {
      return;
    }

    const selectionId = `${selectionScope}:${rowIndex}`;
    const alreadySelected = basket.some((item) => item.selectionId === selectionId);
    if (alreadySelected) {
      setBasket((current) => current.filter((item) => item.selectionId !== selectionId));
      return;
    }

    setBasket((current) => [
      ...current,
      {
        selectionId,
        record: currentRecords[rowIndex],
        mappedRow: currentMappedRows[rowIndex],
      },
    ]);
  }

  async function handleImport() {
    if (!canCreateDataset) {
      setError(buildDisabledReason({
        mode,
        basketCount: basket.length,
        datasetName,
        recordsPath: activeRecordsPath,
        hasMapping: mappingResult.fieldMapping !== null,
      }));
      return;
    }
    if (mappingResult.fieldMapping === null) {
      setError('Define a valid mapping before creating the dataset.');
      return;
    }

    setImporting(true);
    setError(null);
    try {
      if (mode === 'create') {
        const dataset = await importDatasetFromSource({
          name: datasetName.trim(),
          selected_records: basket.map((item) => item.record),
          data_source_id: sourceId,
          records_path: activeRecordsPath,
          field_mapping: mappingResult.fieldMapping,
        });
        onComplete(dataset.id);
        return;
      }

      if (!datasetId) {
        throw new Error('Dataset id is required for append');
      }
      const dataset = await appendDatasetFromSource(
        datasetId,
        basket.map((item) => item.record),
      );
      onComplete(dataset.id);
    } catch (importError) {
      setError(importError instanceof Error ? importError.message : 'Import failed');
    } finally {
      setImporting(false);
    }
  }

  return (
    <div className="space-y-5">
      {error ? (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Explore Response</CardTitle>
            <p className="mt-1 text-xs text-foreground-secondary">
              Inspect the remote JSON and paginate through it. Then choose which array contains the records you want to map.
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => void handleExplore(exploreResult?.previous_page_state)}
              disabled={loading || !exploreResult?.previous_page_state}
            >
              <ArrowLeft className="mr-2 h-4 w-4" />Previous
            </Button>
            <Button
              variant="outline"
              onClick={() => void handleExplore(exploreResult?.next_page_state)}
              disabled={loading || !exploreResult?.next_page_state}
            >
              <ArrowRight className="mr-2 h-4 w-4" />Next
            </Button>
            <Button onClick={() => void handleExplore()} disabled={loading}>
              {loading ? <Spinner className="mr-2" /> : <Download className="mr-2 h-4 w-4" />}
              {loading ? 'Loading...' : 'Explore'}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {mode === 'append' && activeRecordsPath ? (
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="info">Locked Records Path: {activeRecordsPath}</Badge>
            </div>
          ) : null}

          {exploreResult ? (
            <div className="space-y-4">
              <div className="space-y-2">
                <p className="text-sm font-medium text-foreground">Raw JSON</p>
                <JsonTreeView value={exploreResult.raw_response} className="max-h-[520px] overflow-auto" />
              </div>

              {exploreResult.candidate_array_paths.length > 0 ? (
                <details className="rounded-md border border-border bg-background-secondary/60 px-4 py-3">
                  <summary className="cursor-pointer text-sm font-medium text-foreground">
                    Detected Array Paths ({exploreResult.candidate_array_paths.length})
                  </summary>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {exploreResult.candidate_array_paths.map((path) => (
                      <Button
                        key={path}
                        type="button"
                        variant={path === activeRecordsPath ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => void handleSelectRecordsPath(path)}
                      >
                        {path}
                      </Button>
                    ))}
                  </div>
                </details>
              ) : null}

              {mode === 'create' ? (
                <div className="space-y-2 rounded-md border border-border bg-background-secondary/60 p-4">
                  <Label>Records Path</Label>
                  <div className="flex gap-2">
                    <Input
                      value={draftRecordsPath}
                      onChange={(event) => setDraftRecordsPath(event.target.value)}
                      list={`${sourceId}-records-path-options`}
                      placeholder="Select a detected array path or type one manually"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => void handleExplore(exploreResult.current_page_state, draftRecordsPath)}
                      disabled={loading || !draftRecordsPath.trim()}
                    >
                      Load Records
                    </Button>
                  </div>
                  <p className="text-xs text-foreground-secondary">
                    After inspecting the response, choose the array that contains your records. That path drives mapping and basket selection.
                  </p>
                  {activeRecordsPath ? (
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="info">Active Records Path: {activeRecordsPath}</Badge>
                      {presetId ? <Badge>Preset Loaded As Draft</Badge> : null}
                    </div>
                  ) : null}
                  <datalist id={`${sourceId}-records-path-options`}>
                    {exploreResult.candidate_array_paths.map((path) => (
                      <option key={path} value={path} />
                    ))}
                  </datalist>
                </div>
              ) : null}

              {exploreResult.field_candidates.length > 0 ? (
                <details className="rounded-md border border-border bg-background-secondary/60 px-4 py-3">
                  <summary className="cursor-pointer text-sm font-medium text-foreground">
                    Detected Field Paths ({exploreResult.field_candidates.length})
                  </summary>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {exploreResult.field_candidates.map((field) => (
                      <Badge key={field}>{field}</Badge>
                    ))}
                  </div>
                </details>
              ) : null}
            </div>
          ) : (
            <p className="text-sm text-foreground-secondary">
              Run explore first to inspect the JSON response. After that, choose the records path from the detected arrays.
            </p>
          )}
        </CardContent>
      </Card>

      {mode === 'create' ? (
        <Card>
          <CardHeader>
            <CardTitle>Create Mapping</CardTitle>
            <p className="text-sm text-foreground-secondary">
              Define how remote fields become dataset columns. Use single paths like <code>name</code>, compose strings with placeholders like <code>{'{name} - {difficulty}'}</code>, or use a simple condition like <code>{'{logs[].metadata[].lot_id = 12 ? "Lot 12" : "Other lot"}'}</code>.
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Dataset input</Label>
              <Textarea
                value={inputTemplate}
                onChange={(event) => setInputTemplate(event.target.value)}
                rows={4}
                className="font-mono text-xs"
                placeholder={'Recipe: {name}\nLabel: {difficulty == "Easy" ? "Quick" : "Complex"}'}
              />
            </div>

            <div className="space-y-2">
              <Label>Dataset expected_output</Label>
              <Textarea
                value={expectedOutputTemplate}
                onChange={(event) => setExpectedOutputTemplate(event.target.value)}
                rows={4}
                className="font-mono text-xs"
                placeholder={'{logs[].metadata[].lot_id = 12 ? "Lot 12" : "Other lot"}'}
              />
            </div>

            {mappingResult.error ? (
              <Alert variant="destructive">
                <AlertDescription>{mappingResult.error}</AlertDescription>
              </Alert>
            ) : null}

            {saveMappingError ? (
              <Alert variant="destructive">
                <AlertDescription>{saveMappingError}</AlertDescription>
              </Alert>
            ) : null}

            <div className="space-y-2 rounded-md border border-border bg-background-secondary/60 p-4">
              <Label>Saved Mapping Name</Label>
              <div className="flex gap-2">
                <Input
                  value={mappingName}
                  onChange={(event) => setMappingName(event.target.value)}
                  placeholder="Recipe Import Mapping"
                />
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => void handleSaveMapping()}
                  disabled={savingMapping || !onSaveMapping}
                >
                  {savingMapping ? <Spinner className="mr-2" /> : null}
                  {savingMapping
                    ? 'Saving...'
                    : presetId
                      ? 'Update Mapping'
                      : 'Save Mapping'}
                </Button>
              </div>
              <p className="text-xs text-foreground-secondary">
                Saving stores the current records path plus the current input and expected_output mapping.
              </p>
            </div>

            <div className="flex justify-end">
              <Button
                type="button"
                onClick={() => void handleShowMappedData()}
                disabled={loading}
              >
                {loading ? <Spinner className="mr-2" /> : null}
                {loading ? 'Loading...' : 'Show Mapped Data'}
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Mapped Preview</CardTitle>
          <p className="text-sm text-foreground-secondary">
            This is the current page transformed into dataset rows. Add rows from here into the basket.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          {currentMappedRows.length > 0 ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-28">Basket</TableHead>
                    {Object.keys(currentMappedRows[0]).map((column) => (
                      <TableHead key={column}>{column}</TableHead>
                    ))}
                    <TableHead>Raw Record</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {currentMappedRows.map((row, index) => {
                    const selectionId = `${selectionScope}:${index}`;
                    const checked = basket.some((item) => item.selectionId === selectionId);

                    return (
                      <TableRow key={selectionId}>
                        <TableCell>
                          <Button
                            type="button"
                            variant={checked ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => toggleSelection(index)}
                          >
                            {checked ? 'Remove' : 'Add'}
                          </Button>
                        </TableCell>
                        {Object.entries(row).map(([column, value]) => (
                          <TableCell
                            key={column}
                            className="max-w-[240px] whitespace-pre-wrap break-words text-sm"
                          >
                            {value || <span className="text-foreground-disabled italic">empty</span>}
                          </TableCell>
                        ))}
                        <TableCell className="max-w-[320px] whitespace-pre-wrap break-words text-xs text-foreground-secondary">
                          {JSON.stringify(currentRecords[index])}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          ) : currentRecords.length > 0 ? (
            <div className="space-y-3">
              <p className="text-sm text-foreground-secondary">
                Records were found for the current page, but there is no valid mapping preview yet. Fill in <code>input</code> and <code>expected_output</code>, then click <code>Show Mapped Data</code>.
              </p>
              {currentRecords.slice(0, 3).map((record, index) => (
                <div key={`record-preview-${index}`} className="rounded-md border border-border bg-background-secondary/60 p-3">
                  <p className="mb-2 text-sm font-medium text-foreground">Record {index + 1}</p>
                  <JsonTreeView value={record} className="max-h-[260px] overflow-auto" defaultExpandedDepth={1} />
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-foreground-secondary">
              No mapped rows yet. Explore a page and define a valid mapping to see preview rows here.
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Basket</CardTitle>
          <Badge>{basket.length} selected</Badge>
        </CardHeader>
        <CardContent className="space-y-4">
          {mode === 'create' ? (
            <div className="space-y-2 rounded-md border border-border bg-background-secondary/60 p-4">
              <Label>Dataset Name</Label>
              <Input
                value={datasetName}
                onChange={(event) => setDatasetName(event.target.value)}
                placeholder="Imported dataset name"
              />
            </div>
          ) : null}

          {basket.length === 0 ? (
            <p className="text-sm text-foreground-secondary">
              No rows selected yet. Add rows from the mapped preview above.
            </p>
          ) : (
            <div className="space-y-3">
              {basket.map((item) => (
                <div key={item.selectionId} className="rounded-md border border-border bg-background-secondary p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1 space-y-1">
                      {Object.entries(item.mappedRow).map(([column, value]) => (
                        <p key={column} className="text-sm">
                          <span className="text-foreground-secondary">{column}:</span>{' '}
                          <span className="whitespace-pre-wrap break-words">{value || 'empty'}</span>
                        </p>
                      ))}
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setBasket((current) => current.filter((entry) => entry.selectionId !== item.selectionId))}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <Button onClick={() => void handleImport()} disabled={!canCreateDataset || importing}>
            {importing ? <Spinner className="mr-2" /> : null}
            {importing
              ? 'Importing...'
              : mode === 'create'
                ? `Create Dataset (${basket.length})`
                : `Append Rows (${basket.length})`}
          </Button>

          {!canCreateDataset ? (
            <p className="text-xs text-foreground-secondary">
              {buildDisabledReason({
                mode,
                basketCount: basket.length,
                datasetName,
                recordsPath: activeRecordsPath,
                hasMapping: mappingResult.fieldMapping !== null,
              })}
            </p>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}

function splitInitialFieldMapping(fieldMapping?: Record<string, string>): {
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

function buildDraftFieldMapping({
  mode,
  inputTemplate,
  expectedOutputTemplate,
  lockedFieldMapping,
}: {
  mode: 'create' | 'append';
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

function buildDisabledReason({
  mode,
  basketCount,
  datasetName,
  recordsPath,
  hasMapping,
}: {
  mode: 'create' | 'append';
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
