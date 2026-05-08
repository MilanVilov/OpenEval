import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createDataSource } from '@/api/dataSources';
import type { DataSourcePayload } from '@/types/dataSource';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PageHeader } from '@/components/PageHeader';
import { PageTransition } from '@/components/PageTransition';
import { DataSourceForm } from '@/components/dataSources/DataSourceForm';

export function DataSourceNew() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(payload: Partial<DataSourcePayload>) {
    setSubmitting(true);
    setError(null);
    try {
      const source = await createDataSource(payload as DataSourcePayload);
      navigate(`/data-sources/${source.id}`);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Failed to create data source');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <PageTransition>
      <PageHeader title="New Data Source" description="Configure a reusable remote endpoint for dataset import" />
      <Card className="max-w-[960px]">
        <CardHeader>
          <CardTitle>Source Connection</CardTitle>
        </CardHeader>
        <CardContent>
          <DataSourceForm
            mode="create"
            error={error}
            submitting={submitting}
            submitLabel="Create Source"
            onSubmit={handleSubmit}
            onCancel={() => navigate('/data-sources')}
          />
        </CardContent>
      </Card>
    </PageTransition>
  );
}
