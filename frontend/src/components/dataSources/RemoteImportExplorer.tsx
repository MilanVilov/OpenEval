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
  translateInputColumn,
} from '@/api/dataSources';
import { JsonTreeView } from '@/components/JsonTreeView';
import { Spinner } from '@/components/Spinner';
import type {
  ExploreDataSourceRequest,
  ExploreDataSourceResponse,
  JsonValue,
  MappedDataRow,
} from '@/types/dataSource';
import { ArrowLeft, ArrowRight, Download, Languages, RotateCcw, Trash2 } from 'lucide-react';
import {
  buildDisabledReason,
  buildDraftFieldMapping,
  splitInitialFieldMapping,
} from './remoteImportExplorer.helpers';

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
  mappedRow: MappedDataRow;
}

interface TranslatedPageState {
  mappedRows: MappedDataRow[];
  originalInputRowIndexes: number[];
  targetLanguage: string;
}

interface TranslatedPagesState {
  [selectionScope: string]: TranslatedPageState;
}

interface PaginationActionsProps {
  loading: boolean;
  hasPrevious: boolean;
  hasNext: boolean;
  onPrevious: () => void;
  onNext: () => void;
  showExplore?: boolean;
  onExplore?: () => void;
}

function PaginationActions({
  loading,
  hasPrevious,
  hasNext,
  onPrevious,
  onNext,
  showExplore = false,
  onExplore,
}: PaginationActionsProps) {
  return (
    <div className="flex gap-2">
      <Button
        variant="outline"
        onClick={onPrevious}
        disabled={loading || !hasPrevious}
      >
        <ArrowLeft className="mr-2 h-4 w-4" />Previous
      </Button>
      <Button
        variant="outline"
        onClick={onNext}
        disabled={loading || !hasNext}
      >
        <ArrowRight className="mr-2 h-4 w-4" />Next
      </Button>
      {showExplore ? (
        <Button onClick={onExplore} disabled={loading}>
          {loading ? <Spinner className="mr-2" /> : <Download className="mr-2 h-4 w-4" />}
          {loading ? 'Loading...' : 'Explore'}
        </Button>
      ) : null}
    </div>
  );
}

interface InputTranslationActionsProps {
  currentTranslationLanguage: string | null;
  loading: boolean;
  targetLanguage: string;
  onTargetLanguageChange: (value: string) => void;
  onTranslate: () => void;
  onReset: () => void;
}

function InputTranslationActions({
  currentTranslationLanguage,
  loading,
  targetLanguage,
  onTargetLanguageChange,
  onTranslate,
  onReset,
}: InputTranslationActionsProps) {
  return (
    <div className="space-y-3 rounded-md border border-border bg-background-secondary/60 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-foreground">Translate Input Column</p>
          <p className="mt-1 text-xs text-foreground-secondary">
            Uses GPT-5.4 Nano and only changes mapped <code>input</code> values for this page.
          </p>
        </div>
        {currentTranslationLanguage ? (
          <Badge variant="info">Translated to {currentTranslationLanguage}</Badge>
        ) : null}
      </div>

      <div className="flex flex-col gap-2 sm:flex-row">
        <Input
          value={targetLanguage}
          onChange={(event) => onTargetLanguageChange(event.target.value)}
          placeholder="English"
        />
        <Button type="button" variant="outline" onClick={onTranslate} disabled={loading}>
          {loading ? <Spinner className="mr-2" /> : <Languages className="mr-2 h-4 w-4" />}
          {loading ? 'Translating...' : 'Translate'}
        </Button>
        {currentTranslationLanguage ? (
          <Button type="button" variant="ghost" onClick={onReset} disabled={loading}>
            <RotateCcw className="mr-2 h-4 w-4" />
            Reset Page
          </Button>
        ) : null}
      </div>
    </div>
  );
}

function buildSelectionId(selectionScope: string, rowIndex: number): string {
  return `${selectionScope}:${rowIndex}`;
}

function buildDisplayMappedRows(
  originalRows: MappedDataRow[],
  translatedPage: TranslatedPageState | null,
): MappedDataRow[] {
  if (!translatedPage) {
    return originalRows;
  }

  const originalInputRows = new Set(translatedPage.originalInputRowIndexes);
  return translatedPage.mappedRows.map((row, index) => {
    if (!originalInputRows.has(index)) {
      return row;
    }

    return {
      ...row,
      input: originalRows[index]?.input ?? row.input,
    };
  });
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
  const [translatedPages, setTranslatedPages] = useState<TranslatedPagesState>({});
  const [targetLanguage, setTargetLanguage] = useState('English');
  const [loading, setLoading] = useState(false);
  const [translating, setTranslating] = useState(false);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeRecordsPath = mode === 'append' && recordsPath
    ? recordsPath.trim()
    : draftRecordsPath.trim();
  const mappingResult = buildDraftFieldMapping({
    mode,
    inputTemplate,
    expectedOutputTemplate,
    lockedFieldMapping: fieldMapping,
  });
  const selectionScope = JSON.stringify({
    pageState: exploreResult?.current_page_state ?? { page: 'root' },
    recordsPath: activeRecordsPath || '$',
    mapping: mappingResult.fieldMapping ?? null,
  });
  const currentRecords = exploreResult?.records ?? [];
  const currentPageTranslation = translatedPages[selectionScope] ?? null;
  const baseMappedRows = exploreResult?.mapped_rows ?? [];
  const currentMappedRows = buildDisplayMappedRows(baseMappedRows, currentPageTranslation);
  const canCreateDataset = mode === 'append'
    ? basket.length > 0
    : basket.length > 0
        && Boolean(datasetName.trim())
        && Boolean(activeRecordsPath)
        && mappingResult.fieldMapping !== null;

  function syncBasketRowsForScope(scope: string, mappedRows: MappedDataRow[]) {
    const rowsBySelectionId = new Map(
      mappedRows.map((row, index) => [buildSelectionId(scope, index), row]),
    );
    setBasket((current) => current.map((item) => {
      const mappedRow = rowsBySelectionId.get(item.selectionId);
      return mappedRow ? { ...item, mappedRow } : item;
    }));
  }

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

    const selectionId = buildSelectionId(selectionScope, rowIndex);
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

  async function handleTranslateInputColumn() {
    if (!targetLanguage.trim()) {
      setError('Enter a target language before translating the current page.');
      return;
    }
    if (baseMappedRows.length === 0) {
      setError('Load mapped rows for the current page before translating the input column.');
      return;
    }

    setTranslating(true);
    setError(null);
    try {
      const result = await translateInputColumn({
        target_language: targetLanguage.trim(),
        mapped_rows: baseMappedRows,
      });
      setTranslatedPages((current) => ({
        ...current,
        [selectionScope]: {
          mappedRows: result.mapped_rows,
          originalInputRowIndexes: [],
          targetLanguage: targetLanguage.trim(),
        },
      }));
      syncBasketRowsForScope(selectionScope, result.mapped_rows);
    } catch (translationError) {
      setError(translationError instanceof Error ? translationError.message : 'Translation failed');
    } finally {
      setTranslating(false);
    }
  }

  function handleResetPageTranslation() {
    setTranslatedPages((current) => {
      const next = { ...current };
      delete next[selectionScope];
      return next;
    });
    syncBasketRowsForScope(selectionScope, baseMappedRows);
  }

  function toggleShowOriginalInput(rowIndex: number) {
    if (!currentPageTranslation) {
      return;
    }

    const nextOriginalRowIndexes = currentPageTranslation.originalInputRowIndexes.includes(rowIndex)
      ? currentPageTranslation.originalInputRowIndexes.filter((index) => index !== rowIndex)
      : [...currentPageTranslation.originalInputRowIndexes, rowIndex];
    const nextPageTranslation: TranslatedPageState = {
      ...currentPageTranslation,
      originalInputRowIndexes: nextOriginalRowIndexes,
    };
    const nextMappedRows = buildDisplayMappedRows(baseMappedRows, nextPageTranslation);

    setTranslatedPages((current) => ({
      ...current,
      [selectionScope]: nextPageTranslation,
    }));
    syncBasketRowsForScope(selectionScope, nextMappedRows);
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
          selected_rows: basket.map((item) => item.mappedRow),
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
        basket.map((item) => item.mappedRow),
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
          <PaginationActions
            loading={loading}
            hasPrevious={Boolean(exploreResult?.previous_page_state)}
            hasNext={Boolean(exploreResult?.next_page_state)}
            onPrevious={() => void handleExplore(exploreResult?.previous_page_state)}
            onNext={() => void handleExplore(exploreResult?.next_page_state)}
            showExplore
            onExplore={() => void handleExplore()}
          />
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
                      onClick={() => void handleExplore(exploreResult.current_page_state)}
                      disabled={loading || !draftRecordsPath.trim()}
                    >
                      Load Records
                    </Button>
                  </div>
                  <p className="text-xs text-foreground-secondary">
                    This path determines which array items become rows. All mapping expressions and the mapped preview are resolved against records at this path.
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
              Define how remote fields become dataset columns using the expression language below.
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            <details className="rounded-md border border-border bg-background-secondary/60 px-4 py-3">
              <summary className="cursor-pointer text-sm font-medium text-foreground">
                Mapping Expression Reference
              </summary>
              <div className="mt-3 space-y-3 text-sm text-foreground-secondary">
                <div>
                  <p className="font-medium text-foreground">Paths</p>
                  <p>Access fields with dot notation: <code>name</code>, <code>nested.field</code>, <code>items[0].title</code></p>
                  <p>Wildcards expand arrays: <code>{'items[].name'}</code> → all names as a list</p>
                </div>
                <div>
                  <p className="font-medium text-foreground">Templates</p>
                  <p>Compose strings with <code>{'{'}...{'}'}</code> placeholders:</p>
                  <p className="font-mono text-xs">{'Recipe: {name} - Difficulty: {difficulty}'}</p>
                </div>
                <div>
                  <p className="font-medium text-foreground">Conditionals</p>
                  <p>Ternary expressions: <code>{'condition ? true_value : false_value'}</code></p>
                  <p className="font-mono text-xs">{'{difficulty == "Easy" ? "Quick" : "Complex"}'}</p>
                  <p className="font-mono text-xs">{'{logs[].metadata[].lot_id = 12 ? "Lot 12" : "Other lot"}'}</p>
                </div>
                <div>
                  <p className="font-medium text-foreground">parse_json(expr)</p>
                  <p>Parse a JSON string field into an object, then access inner keys:</p>
                  <p className="font-mono text-xs">parse_json(output).key</p>
                  <p className="font-mono text-xs">parse_json(output).confidence</p>
                  <p className="font-mono text-xs">{'{parse_json(output).reasoning}'}</p>
                  <p className="mt-1 text-xs">Useful when a field contains a stringified JSON object like <code>{'"{\\"key\\":\\"value\\"}"'}</code></p>
                </div>
                <div>
                  <p className="font-medium text-foreground">find(array, condition)</p>
                  <p>Find the first item in an array that matches a condition:</p>
                  <p className="font-mono text-xs">{'find(metadata, key == "context").value'}</p>
                  <p className="font-mono text-xs">{'find(tags, id == 1).name'}</p>
                  <p className="mt-1 text-xs">The condition is evaluated against each item in the array. Returns the first match.</p>
                </div>
                <div>
                  <p className="font-medium text-foreground">Combining functions</p>
                  <p>Nest functions to handle complex data like JSON-in-a-string inside arrays:</p>
                  <p className="font-mono text-xs">{'parse_json(find(metadata, key == "context").value).customer_type'}</p>
                  <p className="font-mono text-xs">{'{parse_json(find(metadata, key == "context").value).lot_id}'}</p>
                </div>
              </div>
            </details>

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
                placeholder={'parse_json(find(metadata, key == "context").value).customer_type'}
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
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div>
            <CardTitle>Mapped Preview</CardTitle>
            <p className="text-sm text-foreground-secondary">
              This is the current page transformed into dataset rows. Add rows from here into the basket and paginate through mapped pages here.
            </p>
          </div>
          <PaginationActions
            loading={loading}
            hasPrevious={Boolean(exploreResult?.previous_page_state)}
            hasNext={Boolean(exploreResult?.next_page_state)}
            onPrevious={() => void handleExplore(exploreResult?.previous_page_state)}
            onNext={() => void handleExplore(exploreResult?.next_page_state)}
          />
        </CardHeader>
        <CardContent className="space-y-4">
          {baseMappedRows.length > 0 ? (
            <InputTranslationActions
              currentTranslationLanguage={currentPageTranslation?.targetLanguage ?? null}
              loading={translating}
              targetLanguage={targetLanguage}
              onTargetLanguageChange={setTargetLanguage}
              onTranslate={() => void handleTranslateInputColumn()}
              onReset={handleResetPageTranslation}
            />
          ) : null}

          {currentMappedRows.length > 0 ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-28">Basket</TableHead>
                    {currentPageTranslation ? <TableHead className="w-36">Input View</TableHead> : null}
                    {Object.keys(currentMappedRows[0]).map((column) => (
                      <TableHead key={column}>{column}</TableHead>
                    ))}
                    <TableHead>Raw Record</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {currentMappedRows.map((row, index) => {
                    const selectionId = buildSelectionId(selectionScope, index);
                    const checked = basket.some((item) => item.selectionId === selectionId);
                    const showingOriginalInput = currentPageTranslation?.originalInputRowIndexes.includes(index) ?? false;
                    const inputChanged = Boolean(
                      currentPageTranslation && baseMappedRows[index]?.input !== currentPageTranslation.mappedRows[index]?.input,
                    );

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
                        {currentPageTranslation ? (
                          <TableCell>
                            {inputChanged ? (
                              <Button
                                type="button"
                                variant={showingOriginalInput ? 'default' : 'outline'}
                                size="sm"
                                onClick={() => toggleShowOriginalInput(index)}
                              >
                                {showingOriginalInput ? 'Original' : 'Translated'}
                              </Button>
                            ) : (
                              <span className="text-xs text-foreground-secondary">Same text</span>
                            )}
                          </TableCell>
                        ) : null}
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
