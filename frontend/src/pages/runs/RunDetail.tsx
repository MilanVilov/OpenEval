import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { translateInputColumn } from '@/api/dataSources';
import { deleteRun, exportRun, getRun, getRunProgress, getRunResults } from '@/api/runs';
import { InputTranslationActions } from '@/components/dataSources/InputTranslationActions';
import { ListPagination } from '@/components/ListControls';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { PageHeader } from '@/components/PageHeader';
import { PageTransition } from '@/components/PageTransition';
import { Spinner } from '@/components/Spinner';
import { StatCard } from '@/components/StatCard';
import { StatusBadge } from '@/components/StatusBadge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Popover } from '@/components/ui/popover';
import { Progress } from '@/components/ui/progress';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { usePolling } from '@/hooks/usePolling';
import {
  translateRowsSequentially,
  type RowTranslationProgress,
} from '@/lib/translateRowsSequentially';
import { formatDate, formatPercent, formatTokens } from '@/lib/utils';
import type { EvalResult, EvalRun, GraderStat, RunProgress } from '@/types/run';
import { ArrowDown, ArrowUp, ArrowUpDown, Download, Info, Trash2 } from 'lucide-react';
import { getNextGraderSort, sortResultsByGrader } from './runDetailSorting';
import type { GraderSort } from './runDetailSorting';
import {
  buildRunSourceRows,
  buildRunTranslationScope,
  getRunInputForDisplay,
  type RunResultTranslationState,
} from './runDetailTranslations';

const DEFAULT_PAGE_SIZE = 50;

function isActiveRun(status: string | undefined): boolean {
  return status === 'pending' || status === 'running' || status === 'finalizing';
}

function getEmptyResultsMessage(run: EvalRun, results: EvalResult[]): string {
  if (results.length > 0) {
    return 'No failures found';
  }
  if (run.status === 'finalizing') {
    return 'Finalizing results...';
  }
  return 'No results yet';
}

function buildTranslationErrorMessage(
  error: unknown,
  progress: RowTranslationProgress | null,
  fallbackMessage: string,
): string {
  const baseMessage = error instanceof Error ? error.message : fallbackMessage;
  if (!progress || progress.completed === 0) {
    return baseMessage;
  }
  return `${baseMessage} Translation stopped after ${progress.completed} of ${progress.total} rows.`;
}

export function RunDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [run, setRun] = useState<EvalRun | null>(null);
  const [progress, setProgress] = useState<RunProgress | null>(null);
  const [results, setResults] = useState<EvalResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resultsError, setResultsError] = useState<string | null>(null);
  const [showFailuresOnly, setShowFailuresOnly] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [graderSort, setGraderSort] = useState<GraderSort | null>(null);
  const [targetLanguage, setTargetLanguage] = useState('English');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [translating, setTranslating] = useState(false);
  const [translationProgress, setTranslationProgress] = useState<RowTranslationProgress | null>(null);
  const [translatedPages, setTranslatedPages] = useState<Record<string, RunResultTranslationState>>({});

  const loadResults = useCallback(async (runId: string) => {
    try {
      setResultsError(null);
      setResults(await getRunResults(runId));
    } catch (e) {
      setResultsError(e instanceof Error ? e.message : 'Failed to load evaluation results');
    }
  }, []);

  useEffect(() => {
    if (!id) {
      return;
    }
    const runId = id;
    let cancelled = false;

    async function loadRunDetail(): Promise<void> {
      try {
        setError(null);
        const [nextRun, nextProgress] = await Promise.all([getRun(runId), getRunProgress(runId)]);
        if (cancelled) {
          return;
        }
        setRun(nextRun);
        setProgress(nextProgress);
        setLoading(false);
        void loadResults(runId);
      } catch (e) {
        if (cancelled) {
          return;
        }
        setError(e instanceof Error ? e.message : 'Failed to load evaluation');
        setLoading(false);
      }
    }

    void loadRunDetail();
    return () => {
      cancelled = true;
    };
  }, [id, loadResults]);

  const isRunning = isActiveRun(run?.status);

  const pollCallback = useCallback(async () => {
    if (!id) {
      return;
    }
    try {
      const [updatedRun, nextProgress] = await Promise.all([getRun(id), getRunProgress(id)]);
      setRun(updatedRun);
      setProgress(nextProgress);
      if (!isActiveRun(updatedRun.status)) {
        void loadResults(id);
      }
    } catch (e) {
      setResultsError(e instanceof Error ? e.message : 'Failed to refresh evaluation status');
    }
  }, [id, loadResults]);

  usePolling(pollCallback, 2000, isRunning);

  async function handleDelete() {
    if (!id || !confirm('Delete this run?')) {
      return;
    }
    await deleteRun(id);
    navigate('/runs');
  }

  async function handleExport() {
    if (!id) {
      return;
    }
    setExporting(true);
    setError(null);
    try {
      await exportRun(id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to export evaluation');
    } finally {
      setExporting(false);
    }
  }

  if (loading) {
    return <LoadingSkeleton rows={6} />;
  }
  if (error) {
    return <Alert variant="destructive" className="animate-fade-in"><AlertDescription>{error}</AlertDescription></Alert>;
  }
  if (!run) {
    return <Alert variant="destructive" className="animate-fade-in"><AlertDescription>Run not found</AlertDescription></Alert>;
  }

  const filteredResults = showFailuresOnly ? results.filter((result) => !result.passed) : results;
  const displayedResults = sortResultsByGrader(filteredResults, graderSort);
  const pages = Math.max(1, Math.ceil(displayedResults.length / pageSize));
  const safePage = Math.min(page, pages);
  const currentPageStart = (safePage - 1) * pageSize;
  const currentPageResults = displayedResults.slice(currentPageStart, currentPageStart + pageSize);
  const currentPageScope = buildRunTranslationScope(currentPageResults);
  const currentPageTranslation = translatedPages[currentPageScope] ?? null;
  const canTranslateInputColumn = currentPageResults.length > 0;
  const progressPct = progress ? Math.round((progress.progress / Math.max(progress.total_rows, 1)) * 100) : 0;

  const comparerNames = Array.from(
    new Set(
      results.flatMap((result) => (
        result.comparer_details && typeof result.comparer_details === 'object'
          ? Object.keys(result.comparer_details)
          : []
      )),
    ),
  );

  const graderStats: Record<string, GraderStat> | undefined = run.summary?.grader_stats;
  const hasMultipleGraders = !!graderStats && Object.keys(graderStats).length >= 2;

  const weightByComparer: Record<string, number> = {};
  for (const result of results) {
    if (!result.comparer_details) {
      continue;
    }
    for (const [comparerName, detail] of Object.entries(result.comparer_details)) {
      if (comparerName in weightByComparer) {
        continue;
      }
      const typedDetail = detail as Record<string, unknown> | undefined;
      weightByComparer[comparerName] = typeof typedDetail?.weight === 'number' ? typedDetail.weight : 1;
    }
  }

  async function handleTranslatePage() {
    if (!currentPageResults.length) {
      setResultsError('There are no run rows on this page to translate.');
      return;
    }
    if (!targetLanguage.trim()) {
      setResultsError('Enter a target language before translating this page.');
      return;
    }

    setTranslating(true);
    setResultsError(null);
    let latestProgress: RowTranslationProgress | null = null;
    try {
      const sourceRows = buildRunSourceRows(currentPageResults, currentPageTranslation);
      setTranslatedPages((current) => ({
        ...current,
        [currentPageScope]: {
          resultIds: currentPageResults.map((result) => result.id),
          originalInputs: sourceRows.map((row) => row.input),
          originalInputRowIndexes: [],
          targetLanguage: targetLanguage.trim(),
          translatedInputs: sourceRows.map((row) => row.input),
        },
      }));
      await translateRowsSequentially({
        rows: sourceRows,
        targetLanguage: targetLanguage.trim(),
        translateRow: async (row, language) => {
          const result = await translateInputColumn({
            target_language: language,
            mapped_rows: [row],
          });
          const translatedRow = result.mapped_rows[0];
          if (!translatedRow) {
            throw new Error('Translation response was empty for one of the run rows.');
          }
          return {
            input: translatedRow.input ?? '',
          };
        },
        onProgress: (progressUpdate) => {
          latestProgress = progressUpdate;
          setTranslationProgress(progressUpdate);
        },
        onRowTranslated: (rowIndex, translatedRow) => {
          setTranslatedPages((current) => {
            const existingPage = current[currentPageScope];
            if (!existingPage) {
              return current;
            }
            const nextTranslatedInputs = [...existingPage.translatedInputs];
            nextTranslatedInputs[rowIndex] = translatedRow.input ?? '';
            return {
              ...current,
              [currentPageScope]: {
                ...existingPage,
                translatedInputs: nextTranslatedInputs,
              },
            };
          });
        },
      });
    } catch (e) {
      setResultsError(buildTranslationErrorMessage(e, latestProgress, 'Failed to translate the run page'));
    } finally {
      setTranslating(false);
      setTranslationProgress(null);
    }
  }

  function handleResetPageTranslation() {
    setTranslatedPages((current) => {
      const next = { ...current };
      delete next[currentPageScope];
      return next;
    });
  }

  function toggleShowOriginalInput(rowIndex: number) {
    if (!currentPageTranslation || translating) {
      return;
    }

    const nextOriginalRowIndexes = currentPageTranslation.originalInputRowIndexes.includes(rowIndex)
      ? currentPageTranslation.originalInputRowIndexes.filter((index) => index !== rowIndex)
      : [...currentPageTranslation.originalInputRowIndexes, rowIndex];
    setTranslatedPages((current) => ({
      ...current,
      [currentPageScope]: {
        ...currentPageTranslation,
        originalInputRowIndexes: nextOriginalRowIndexes,
      },
    }));
  }

  function handlePageChange(nextPage: number) {
    if (translating) {
      return;
    }
    setPage(nextPage);
  }

  function handlePageSizeChange(nextPageSize: number) {
    if (translating) {
      return;
    }
    setPageSize(nextPageSize);
    setPage(1);
  }

  return (
    <PageTransition>
      <PageHeader
        title={`Run: ${run.config_name ?? 'Unknown'}`}
        description={`Dataset: ${run.dataset_name ?? 'Unknown'} · ${formatDate(run.created_at)}`}
        action={
          <div className="flex items-center gap-2">
            <StatusBadge status={run.status} />
            <Button variant="outline" size="sm" onClick={() => void handleExport()} disabled={exporting || translating}>
              <Download className="mr-2 h-4 w-4" />
              {exporting ? 'Exporting...' : 'Export CSV'}
            </Button>
            <Button variant="destructive" size="sm" onClick={handleDelete} disabled={translating}>
              <Trash2 className="mr-2 h-4 w-4" />Delete
            </Button>
          </div>
        }
      />

      {isRunning && progress ? (
        <Card className="mb-4">
          <CardContent className="pt-4">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-sm text-foreground-secondary">Progress</span>
              <span className="text-sm font-medium">{progress.progress}/{progress.total_rows}</span>
            </div>
            <Progress value={progressPct} />
            <div className="mt-2 flex gap-4 text-xs text-foreground-secondary">
              <span>Status: {progress.status}</span>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {run.status === 'failed' && run.error_message ? (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription className="whitespace-pre-wrap">
            <span className="font-medium">Run failed:</span> {run.error_message}
          </AlertDescription>
        </Alert>
      ) : null}

      {run.summary ? (
        <div className="mb-6 grid grid-cols-2 gap-4 animate-fade-in md:grid-cols-4 lg:grid-cols-7">
          {hasMultipleGraders ? (
            <Popover
              align="start"
              className="min-w-[200px]"
              trigger={(
                <StatCard
                  label="Accuracy"
                  value={formatPercent(run.summary.accuracy)}
                  icon={<Info className="h-3 w-3 text-foreground-secondary" />}
                />
              )}
            >
              <div className="mb-2 text-xs font-medium uppercase tracking-wide text-foreground-secondary">
                Avg Score by Grader
              </div>
              <div className="space-y-1.5">
                {Object.entries(graderStats).map(([name, stat]) => (
                  <div key={name} className="flex items-center justify-between gap-4 text-sm">
                    <span className="truncate text-foreground-secondary">{name}</span>
                    <span className="font-mono font-medium tabular-nums text-foreground">
                      {stat.avg_score.toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            </Popover>
          ) : (
            <StatCard label="Accuracy" value={formatPercent(run.summary.accuracy)} />
          )}
          <StatCard label="Total" value={String(run.summary.total)} />
          <StatCard label="Passed" value={String(run.summary.passed)} />
          <StatCard label="Failed" value={String(run.summary.failed)} />
          <StatCard label="Avg Latency" value={`${run.summary.avg_latency_ms}ms`} />
          <StatCard label="Avg Input Tokens" value={formatTokens(run.summary.avg_input_tokens ?? 0)} />
          <StatCard label="Avg Output Tokens" value={formatTokens(run.summary.avg_output_tokens ?? 0)} />
        </div>
      ) : null}

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Results</CardTitle>
              <p className="mt-1 text-xs text-foreground-secondary">
                CSV export includes row outputs, grader reasoning, latency, token usage, and raw comparer details.
              </p>
            </div>
            <Button
              variant={showFailuresOnly ? 'default' : 'outline'}
              size="sm"
              onClick={() => {
                if (translating) {
                  return;
                }
                setShowFailuresOnly(!showFailuresOnly);
                setPage(1);
              }}
              disabled={translating}
            >
              {showFailuresOnly ? 'Show All' : 'Failures Only'}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {canTranslateInputColumn ? (
            <InputTranslationActions
              currentTranslationLanguage={currentPageTranslation?.targetLanguage ?? null}
              loading={translating}
              progress={translationProgress}
              targetLanguage={targetLanguage}
              onTargetLanguageChange={setTargetLanguage}
              onTranslate={() => void handleTranslatePage()}
              onReset={handleResetPageTranslation}
            />
          ) : null}

          {resultsError ? (
            <Alert variant="destructive">
              <AlertDescription>{resultsError}</AlertDescription>
            </Alert>
          ) : null}

          {displayedResults.length === 0 ? (
            <p className="py-4 text-sm text-foreground-secondary">
              {getEmptyResultsMessage(run, results)}
            </p>
          ) : (
            <>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-12">#</TableHead>
                      {currentPageTranslation ? <TableHead className="w-36">Input View</TableHead> : null}
                      <TableHead>Input</TableHead>
                      <TableHead>Expected</TableHead>
                      <TableHead>Actual</TableHead>
                      {comparerNames.length > 0 ? (
                        comparerNames.map((name) => {
                          const weight = weightByComparer[name] ?? 1;
                          const isSorted = graderSort?.graderName === name;
                          const sortDirection = isSorted ? graderSort.direction : null;
                          return (
                            <TableHead
                              key={name}
                              className="w-28 text-center"
                              aria-sort={
                                sortDirection === 'fail-first'
                                  ? 'ascending'
                                  : sortDirection === 'pass-first'
                                    ? 'descending'
                                    : 'none'
                              }
                            >
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-auto w-full justify-center gap-1.5 px-2 py-1"
                                onClick={() => {
                                  if (translating) {
                                    return;
                                  }
                                  setGraderSort((currentSort) => getNextGraderSort(currentSort, name));
                                  setPage(1);
                                }}
                                disabled={translating}
                                title={
                                  !isSorted
                                    ? `Sort ${name}: failed rows first`
                                    : sortDirection === 'fail-first'
                                      ? `Sort ${name}: passed rows first`
                                      : `Clear ${name} sorting`
                                }
                              >
                                <span className={weight === 0 ? 'opacity-50' : ''}>{name}</span>
                                {weight !== 1 ? (
                                  <Badge variant="default" className="px-1 py-0 text-[10px]">
                                    w:{weight}
                                  </Badge>
                                ) : null}
                                {hasMultipleGraders && graderStats?.[name] ? (
                                  <Badge variant="default" className="px-1.5 py-0 text-[10px]">
                                    {formatPercent(graderStats[name].accuracy)}
                                  </Badge>
                                ) : null}
                                {sortDirection === 'fail-first' ? (
                                  <ArrowUp className="h-3.5 w-3.5 shrink-0" />
                                ) : sortDirection === 'pass-first' ? (
                                  <ArrowDown className="h-3.5 w-3.5 shrink-0" />
                                ) : (
                                  <ArrowUpDown className="h-3.5 w-3.5 shrink-0 text-foreground-secondary" />
                                )}
                              </Button>
                            </TableHead>
                          );
                        })
                      ) : (
                        <TableHead className="w-20">Match</TableHead>
                      )}
                      <TableHead className="w-20">Score</TableHead>
                      <TableHead className="w-24">Latency</TableHead>
                      <TableHead className="w-28">Tokens (in/out)</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {currentPageResults.map((result, rowIndex) => {
                      const inputChanged = Boolean(
                        currentPageTranslation
                        && currentPageTranslation.originalInputs[rowIndex] !== currentPageTranslation.translatedInputs[rowIndex],
                      );
                      const showingOriginalInput = currentPageTranslation?.originalInputRowIndexes.includes(rowIndex) ?? false;
                      const activeTranslationRowIndex = translationProgress?.activeRowIndex ?? null;
                      const activeTranslationRow = translating && activeTranslationRowIndex === rowIndex;
                      const pendingTranslationRow = translating
                        && activeTranslationRowIndex !== null
                        && rowIndex > activeTranslationRowIndex;

                      return (
                        <TableRow key={result.id}>
                          <TableCell>{result.row_index}</TableCell>
                          {currentPageTranslation ? (
                            <TableCell>
                              {activeTranslationRow ? (
                                <Badge variant="info" className="gap-1">
                                  <Spinner className="h-3 w-3" />
                                  Translating
                                </Badge>
                              ) : pendingTranslationRow ? (
                                <Badge>Pending</Badge>
                              ) : inputChanged ? (
                                <Button
                                  type="button"
                                  variant={showingOriginalInput ? 'default' : 'outline'}
                                  size="sm"
                                  onClick={() => toggleShowOriginalInput(rowIndex)}
                                  disabled={translating}
                                >
                                  {showingOriginalInput ? 'Original' : 'Translated'}
                                </Button>
                              ) : (
                                <Badge>Same text</Badge>
                              )}
                            </TableCell>
                          ) : null}
                          <TableCell className="min-w-[200px] max-w-[400px] whitespace-pre-wrap break-words">
                            {getRunInputForDisplay(result, rowIndex, currentPageTranslation)}
                          </TableCell>
                          <TableCell className="min-w-[200px] max-w-[400px] whitespace-pre-wrap break-words">
                            {result.expected_output}
                          </TableCell>
                          <TableCell className="min-w-[200px] max-w-[400px] whitespace-pre-wrap break-words">
                            {result.actual_output ?? (
                              result.error ? (
                                <span className="text-xs text-red-400">{result.error}</span>
                              ) : '—'
                            )}
                          </TableCell>
                          {comparerNames.length > 0 ? (
                            comparerNames.map((name) => {
                              const detail = result.comparer_details?.[name] as Record<string, unknown> | undefined;
                              if (!detail) {
                                return <TableCell key={name} className="text-center">—</TableCell>;
                              }
                              const passed = detail.passed as boolean | undefined;
                              return (
                                <TableCell key={name} className="text-center" title={JSON.stringify(detail, null, 2)}>
                                  <Badge variant={passed ? 'success' : 'error'}>
                                    {passed ? 'Pass' : 'Fail'}
                                  </Badge>
                                </TableCell>
                              );
                            })
                          ) : (
                            <TableCell>
                              <Badge variant={result.passed ? 'success' : 'error'}>
                                {result.passed ? 'Pass' : 'Fail'}
                              </Badge>
                            </TableCell>
                          )}
                          <TableCell>{result.comparer_score != null ? result.comparer_score.toFixed(2) : '—'}</TableCell>
                          <TableCell>{result.latency_ms != null ? `${result.latency_ms}ms` : '—'}</TableCell>
                          <TableCell className="tabular-nums">
                            {result.token_usage
                              ? `${formatTokens(result.token_usage.input_tokens)} / ${formatTokens(result.token_usage.output_tokens)}`
                              : '—'}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>

              <ListPagination
                page={safePage}
                pageSize={pageSize}
                pages={pages}
                total={displayedResults.length}
                itemLabel="results"
                onPageChange={handlePageChange}
                onPageSizeChange={handlePageSizeChange}
              />
            </>
          )}
        </CardContent>
      </Card>
    </PageTransition>
  );
}
