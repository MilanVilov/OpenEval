import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  createImportPreset,
  duplicateDataSource,
  deleteDataSource,
  deleteImportPreset,
  getDataSource,
  listImportPresets,
  updateDataSource,
  updateImportPreset,
} from '@/api/dataSources';
import type { DataSourceDetail as DataSourceDetailType, DataSourcePayload, ImportPreset, ImportPresetPayload } from '@/types/dataSource';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { PageHeader } from '@/components/PageHeader';
import { PageTransition } from '@/components/PageTransition';
import { DataSourceForm } from '@/components/dataSources/DataSourceForm';
import { RemoteImportExplorer } from '@/components/dataSources/RemoteImportExplorer';
import { Copy, Plus, Trash2 } from 'lucide-react';

export function DataSourceDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [source, setSource] = useState<DataSourceDetailType | null>(null);
  const [presets, setPresets] = useState<ImportPreset[]>([]);
  const [selectedPresetId, setSelectedPresetId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [sourceSubmitting, setSourceSubmitting] = useState(false);
  const [presetSubmitting, setPresetSubmitting] = useState(false);
  const [duplicating, setDuplicating] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [sourceError, setSourceError] = useState<string | null>(null);
  const [presetError, setPresetError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) {
      return;
    }
    void loadPage(id);
  }, [id]);

  async function loadPage(sourceId: string) {
    setLoading(true);
    setPageError(null);
    try {
      const [nextSource, nextPresets] = await Promise.all([
        getDataSource(sourceId),
        listImportPresets(sourceId),
      ]);
      setSource(nextSource);
      setPresets(nextPresets);
      setSelectedPresetId(nextPresets[0]?.id ?? null);
    } catch (loadError) {
      setPageError(loadError instanceof Error ? loadError.message : 'Failed to load data source');
    } finally {
      setLoading(false);
    }
  }

  async function handleSourceSave(payload: Partial<DataSourcePayload>) {
    if (!id) {
      return;
    }
    setSourceSubmitting(true);
    setSourceError(null);
    try {
      const updated = await updateDataSource(id, payload);
      setSource(updated);
    } catch (saveError) {
      setSourceError(saveError instanceof Error ? saveError.message : 'Failed to save data source');
    } finally {
      setSourceSubmitting(false);
    }
  }

  async function handleDeleteSource() {
    if (!id || !confirm('Delete this data source?')) {
      return;
    }
    try {
      await deleteDataSource(id);
      navigate('/data-sources');
    } catch (deleteError) {
      setPageError(deleteError instanceof Error ? deleteError.message : 'Failed to delete data source');
    }
  }

  async function handleDuplicateSource() {
    if (!id) {
      return;
    }
    setDuplicating(true);
    setPageError(null);
    try {
      const duplicate = await duplicateDataSource(id);
      navigate(`/data-sources/${duplicate.id}`);
    } catch (duplicateError) {
      setPageError(duplicateError instanceof Error ? duplicateError.message : 'Failed to duplicate data source');
    } finally {
      setDuplicating(false);
    }
  }

  async function handlePresetSave(payload: ImportPresetPayload) {
    if (!id) {
      return;
    }
    setPresetSubmitting(true);
    setPresetError(null);
    try {
      if (selectedPresetId) {
        const updated = await updateImportPreset(id, selectedPresetId, payload);
        setPresets((current) => current.map((preset) => (preset.id === updated.id ? updated : preset)));
        setSelectedPresetId(updated.id);
      } else {
        const created = await createImportPreset(id, payload);
        setPresets((current) => [created, ...current]);
        setSelectedPresetId(created.id);
      }
    } catch (saveError) {
      setPresetError(saveError instanceof Error ? saveError.message : 'Failed to save preset');
    } finally {
      setPresetSubmitting(false);
    }
  }

  async function handleDeletePreset() {
    if (!id || !selectedPresetId || !confirm('Delete this preset?')) {
      return;
    }
    try {
      await deleteImportPreset(id, selectedPresetId);
      const remaining = presets.filter((preset) => preset.id !== selectedPresetId);
      setPresets(remaining);
      setSelectedPresetId(remaining[0]?.id ?? null);
    } catch (deleteError) {
      setPresetError(deleteError instanceof Error ? deleteError.message : 'Failed to delete preset');
    }
  }

  if (loading) return <LoadingSkeleton rows={6} />;
  if (pageError && !source) {
    return <Alert variant="destructive"><AlertDescription>{pageError}</AlertDescription></Alert>;
  }
  if (!source || !id) {
    return <Alert variant="destructive"><AlertDescription>Data source not found</AlertDescription></Alert>;
  }

  const selectedPreset = presets.find((preset) => preset.id === selectedPresetId) ?? null;

  return (
    <PageTransition>
      <PageHeader
        title={source.name}
        description="Update the connection, manage saved mappings, and import selected rows into datasets."
        action={(
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => void handleDuplicateSource()} disabled={duplicating}>
              <Copy className="mr-2 h-4 w-4" />{duplicating ? 'Duplicating…' : 'Duplicate'}
            </Button>
            <Button variant="destructive" size="sm" onClick={handleDeleteSource}>
              <Trash2 className="mr-2 h-4 w-4" />Delete Source
            </Button>
          </div>
        )}
      />

      {pageError ? (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{pageError}</AlertDescription>
        </Alert>
      ) : null}

      <div className="space-y-5">
        <Card>
          <CardHeader>
            <CardTitle>Connection Settings</CardTitle>
          </CardHeader>
          <CardContent>
            <DataSourceForm
              key={`source-${source.id}-${source.updated_at}`}
              mode="edit"
              initial={source}
              error={sourceError}
              submitting={sourceSubmitting}
              submitLabel="Save Source"
              onSubmit={handleSourceSave}
            />
          </CardContent>
        </Card>

        <RemoteImportExplorer
          key={selectedPreset ? `explorer-${selectedPreset.id}` : 'explorer-draft'}
          sourceId={id}
          mode="create"
          presetId={selectedPresetId ?? undefined}
          selectedPresetName={selectedPreset?.name}
          recordsPath={selectedPreset?.records_path}
          fieldMapping={selectedPreset?.field_mapping}
          savingMapping={presetSubmitting}
          saveMappingError={presetError}
          onSaveMapping={handlePresetSave}
          onComplete={(datasetId) => navigate(`/datasets/${datasetId}`)}
        />

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Saved Mappings</CardTitle>
              <p className="mt-1 text-xs text-foreground-secondary">
                Switch between saved mappings here. Creating or updating the mapping happens in the explorer section above.
              </p>
            </div>
            <Button variant="outline" size="sm" onClick={() => setSelectedPresetId(null)}>
              <Plus className="mr-2 h-4 w-4" />New Draft
            </Button>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-2">
              {presets.map((preset) => (
                <button
                  key={preset.id}
                  type="button"
                  onClick={() => setSelectedPresetId(preset.id)}
                  className={`rounded-md border px-3 py-1.5 text-sm transition-colors duration-150 ${
                    preset.id === selectedPresetId
                      ? 'border-border-focus bg-accent-muted text-foreground'
                      : 'border-border bg-background-secondary text-foreground-secondary hover:text-foreground'
                  }`}
                >
                  {preset.name}
                </button>
              ))}
              {presets.length === 0 ? <Badge>No presets yet</Badge> : null}
            </div>

            {selectedPreset ? (
              <div className="flex items-center justify-between gap-3 rounded-md border border-border bg-background-secondary/60 p-3">
                <div className="space-y-1">
                  <p className="text-sm font-medium text-foreground">{selectedPreset.name}</p>
                  <p className="text-xs text-foreground-secondary">
                    Records path: <code>{selectedPreset.records_path}</code>
                  </p>
                </div>
                <Button variant="destructive" size="sm" onClick={() => void handleDeletePreset()}>
                  <Trash2 className="mr-2 h-4 w-4" />Delete Mapping
                </Button>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </PageTransition>
  );
}
