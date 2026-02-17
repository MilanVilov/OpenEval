import { useState, useRef, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { uploadDataset } from '@/api/datasets';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Upload } from 'lucide-react';
import { PageTransition } from '@/components/PageTransition';
import { Spinner } from '@/components/Spinner';

export function DatasetNew() {
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);
  const [name, setName] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) {
      setError('Please select a CSV file');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const dataset = await uploadDataset(name, file);
      navigate(`/datasets/${dataset.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <PageTransition>
      <PageHeader title="Upload Dataset" description="Upload a CSV file for evaluation" />
      <form onSubmit={handleSubmit} className="space-y-5 max-w-[640px]">
        {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

        <div className="space-y-2">
          <Label>Dataset Name</Label>
          <Input value={name} onChange={(e) => setName(e.target.value)} required placeholder="My dataset" />
        </div>

        <div className="space-y-2">
          <Label>CSV File</Label>
          <div className="border border-border rounded-md p-4 bg-background-input">
            <input ref={fileRef} type="file" accept=".csv" className="text-sm text-foreground-secondary file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-medium file:bg-accent-blue file:text-white hover:file:bg-accent-blue/90" />
          </div>
          <p className="text-xs text-foreground-secondary">CSV must have 'input' and 'expected_output' columns.</p>
        </div>

        <div className="flex justify-end gap-2 pt-4">
          <Button type="button" variant="outline" onClick={() => navigate('/datasets')}>Cancel</Button>
          <Button type="submit" disabled={submitting}>
            {submitting ? <Spinner className="mr-2" /> : <Upload className="mr-2 h-4 w-4" />}
            {submitting ? 'Uploading...' : 'Upload'}
          </Button>
        </div>
      </form>
    </PageTransition>
  );
}
