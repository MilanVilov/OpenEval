import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { createContainer } from '@/api/containers';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';

export function ContainerNew() {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const container = await createContainer({ name });
      navigate(`/containers/${container.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create container');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <PageHeader title="New Container" description="Create a new OpenAI container for the shell tool" />
      <form onSubmit={handleSubmit} className="space-y-4 max-w-[600px]">
        {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

        <div className="space-y-2">
          <Label>Name</Label>
          <Input value={name} onChange={(e) => setName(e.target.value)} required placeholder="My container" />
        </div>

        <div className="flex justify-end gap-2 pt-4">
          <Button type="button" variant="outline" onClick={() => navigate('/containers')}>Cancel</Button>
          <Button type="submit" disabled={submitting}>{submitting ? 'Creating...' : 'Create'}</Button>
        </div>
      </form>
    </div>
  );
}
