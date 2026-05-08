import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { getDataset } from '@/api/datasets';
import type { DatasetDetail } from '@/types/dataset';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { PageHeader } from '@/components/PageHeader';
import { PageTransition } from '@/components/PageTransition';
import { RemoteImportExplorer } from '@/components/dataSources/RemoteImportExplorer';

export function DatasetImport() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [dataset, setDataset] = useState<DatasetDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) {
      return;
    }
    getDataset(id)
      .then(setDataset)
      .catch((loadError: Error) => setError(loadError.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <LoadingSkeleton rows={5} />;
  if (error && !dataset) {
    return <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>;
  }
  if (!dataset || !dataset.import_source_snapshot || !id) {
    return <Alert variant="destructive"><AlertDescription>This dataset does not support continue import.</AlertDescription></Alert>;
  }

  const snapshot = dataset.import_source_snapshot;

  return (
    <PageTransition>
      <PageHeader
        title={`Continue Import: ${dataset.name}`}
        description="Explore the original source again, keep a basket across pages, and append the selected rows into this dataset."
      />

      <div className="space-y-5">
        <Card>
          <CardHeader>
            <CardTitle>Locked Mapping</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Badge>Source {snapshot.data_source_id}</Badge>
            <p className="text-sm text-foreground-secondary">Records path: <code>{snapshot.records_path}</code></p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(snapshot.field_mapping).map(([column, path]) => (
                <Badge key={column} variant="info">{column} ← {path}</Badge>
              ))}
            </div>
          </CardContent>
        </Card>

        <RemoteImportExplorer
          sourceId={snapshot.data_source_id}
          mode="append"
          datasetId={id}
          recordsPath={snapshot.records_path}
          fieldMapping={snapshot.field_mapping}
          defaultDatasetName={dataset.name}
          onComplete={() => navigate(`/datasets/${id}`)}
        />
      </div>
    </PageTransition>
  );
}
