import { useState, useEffect, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { createRun } from '@/api/runs';
import { listConfigs } from '@/api/configs';
import { listDatasets } from '@/api/datasets';
import type { EvalConfig } from '@/types/config';
import type { Dataset } from '@/types/dataset';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Play } from 'lucide-react';

export function RunNew() {
  const navigate = useNavigate();
  const [configs, setConfigs] = useState<EvalConfig[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [configId, setConfigId] = useState('');
  const [datasetId, setDatasetId] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([listConfigs(), listDatasets()])
      .then(([c, d]) => {
        setConfigs(c);
        setDatasets(d);
        if (c.length > 0) setConfigId(c[0].id);
        if (d.length > 0) setDatasetId(d[0].id);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!configId || !datasetId) return;
    setSubmitting(true);
    setError(null);
    try {
      const run = await createRun({ eval_config_id: configId, dataset_id: datasetId });
      navigate(`/runs/${run.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start run');
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <Skeleton className="h-40 w-full" />;

  return (
    <div>
      <PageHeader title="Start Evaluation Run" description="Select a config and dataset to evaluate" />
      <form onSubmit={handleSubmit} className="space-y-4 max-w-[600px]">
        {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

        {configs.length === 0 && (
          <Alert><AlertDescription>No configs available. Create a config first.</AlertDescription></Alert>
        )}

        {datasets.length === 0 && (
          <Alert><AlertDescription>No datasets available. Upload a dataset first.</AlertDescription></Alert>
        )}

        <div className="space-y-2">
          <Label>Config</Label>
          <Select value={configId} onChange={(e) => setConfigId(e.target.value)} disabled={configs.length === 0}>
            {configs.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </Select>
        </div>

        <div className="space-y-2">
          <Label>Dataset</Label>
          <Select value={datasetId} onChange={(e) => setDatasetId(e.target.value)} disabled={datasets.length === 0}>
            {datasets.map((d) => (
              <option key={d.id} value={d.id}>{d.name} ({d.row_count} rows)</option>
            ))}
          </Select>
        </div>

        <div className="flex justify-end gap-2 pt-4">
          <Button type="button" variant="outline" onClick={() => navigate('/runs')}>Cancel</Button>
          <Button type="submit" disabled={submitting || configs.length === 0 || datasets.length === 0}>
            <Play className="mr-2 h-4 w-4" />
            {submitting ? 'Starting...' : 'Start Run'}
          </Button>
        </div>
      </form>
    </div>
  );
}
