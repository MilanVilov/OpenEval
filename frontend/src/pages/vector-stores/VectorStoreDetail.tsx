import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getVectorStore, uploadFileToVectorStore, deleteVectorStore } from '@/api/vectorStores';
import type { VectorStore } from '@/types/vectorStore';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { StatCard } from '@/components/StatCard';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { PageTransition } from '@/components/PageTransition';
import { Spinner } from '@/components/Spinner';
import { formatDate } from '@/lib/utils';
import { Trash2, Upload } from 'lucide-react';

export function VectorStoreDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);
  const [store, setStore] = useState<VectorStore | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    getVectorStore(id)
      .then(setStore)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  async function handleUpload() {
    const file = fileRef.current?.files?.[0];
    if (!id || !file) return;
    setUploading(true);
    setUploadMsg(null);
    try {
      const updated = await uploadFileToVectorStore(id, file);
      setStore(updated);
      setUploadMsg('File uploaded successfully');
      if (fileRef.current) fileRef.current.value = '';
    } catch (err) {
      setUploadMsg(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete() {
    if (!id || !confirm('Delete this vector store?')) return;
    await deleteVectorStore(id);
    navigate('/vector-stores');
  }

  if (loading) return <LoadingSkeleton rows={3} />;
  if (error) return <Alert variant="destructive" className="animate-fade-in"><AlertDescription>{error}</AlertDescription></Alert>;
  if (!store) return <Alert variant="destructive" className="animate-fade-in"><AlertDescription>Vector store not found</AlertDescription></Alert>;

  return (
    <PageTransition>
      <PageHeader
        title={store.name}
        description={`Created ${formatDate(store.created_at)}`}
        action={
          <Button variant="destructive" size="sm" onClick={handleDelete}>
            <Trash2 className="mr-2 h-4 w-4" />Delete
          </Button>
        }
      />

      <div className="grid grid-cols-2 gap-4 mb-6">
        <StatCard label="Files" value={String(store.file_count)} />
        <StatCard label="OpenAI ID" value={store.openai_vector_store_id ?? '—'} />
      </div>

      <Card>
        <CardHeader><CardTitle>Upload File</CardTitle></CardHeader>
        <CardContent>
          <div className="flex items-center gap-3">
            <input
              ref={fileRef}
              type="file"
              className="text-sm text-foreground-secondary file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-medium file:bg-accent-blue file:text-white hover:file:bg-accent-blue/90"
            />
            <Button size="sm" onClick={handleUpload} disabled={uploading}>
              {uploading ? <Spinner className="mr-2" /> : <Upload className="mr-2 h-4 w-4" />}
              {uploading ? 'Uploading...' : 'Upload'}
            </Button>
          </div>
          {uploadMsg && <p className="text-sm mt-2 text-foreground-secondary">{uploadMsg}</p>}
        </CardContent>
      </Card>
    </PageTransition>
  );
}
