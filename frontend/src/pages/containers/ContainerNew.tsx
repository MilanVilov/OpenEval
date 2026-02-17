import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { createContainer } from '@/api/containers';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Slider } from '@/components/ui/slider';
import { PageTransition } from '@/components/PageTransition';
import { Spinner } from '@/components/Spinner';

export function ContainerNew() {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [expiresMinutes, setExpiresMinutes] = useState(20);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const container = await createContainer({ name, expires_after_minutes: expiresMinutes });
      navigate(`/containers/${container.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create container');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <PageTransition>
      <PageHeader title="New Container" description="Create a new OpenAI container for the shell tool" />
      <form onSubmit={handleSubmit} className="space-y-5 max-w-[640px]">
        {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

        <div className="space-y-2">
          <Label>Name</Label>
          <Input value={name} onChange={(e) => setName(e.target.value)} required placeholder="My container" />
        </div>

        <div className="space-y-2">
          <Label>Idle Timeout: {expiresMinutes} min</Label>
          <Slider
            min={1}
            max={20}
            step={1}
            value={[expiresMinutes]}
            onValueChange={(v) => setExpiresMinutes(v[0])}
          />
          <p className="text-xs text-muted-foreground">
            Container expires after this many minutes of inactivity (1-20). Timer resets on each use.
          </p>
        </div>

        <div className="flex justify-end gap-2 pt-4">
          <Button type="button" variant="outline" onClick={() => navigate('/containers')}>Cancel</Button>
          <Button type="submit" disabled={submitting}>
            {submitting && <Spinner className="mr-2" />}
            {submitting ? 'Creating...' : 'Create'}
          </Button>
        </div>
      </form>
    </PageTransition>
  );
}
