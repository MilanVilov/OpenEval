import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { listConfigsPage, duplicateConfig, fetchAllTags } from '@/api/configs';
import type { EvalConfig } from '@/types/config';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { PageTransition } from '@/components/PageTransition';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Copy, Lock, Plus } from 'lucide-react';
import { formatDate } from '@/lib/utils';
import { TagFilter } from '@/components/TagFilter';
import { ListControls } from '@/components/ListControls';

export function ConfigList() {
  const [configs, setConfigs] = useState<EvalConfig[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSizeValue] = useState(10);
  const [pages, setPages] = useState(1);
  const [search, setSearchValue] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [duplicatingId, setDuplicatingId] = useState<string | null>(null);
  const [allTags, setAllTags] = useState<string[]>([]);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);

  const loadConfigs = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const result = await listConfigsPage({
        page,
        page_size: pageSize,
        search,
        tags: selectedTags,
      });
      setConfigs(result.items);
      setTotal(result.total);
      setPages(result.pages);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load configs');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search, selectedTags]);

  useEffect(() => {
    void loadConfigs();
  }, [loadConfigs]);

  useEffect(() => {
    fetchAllTags()
      .then(setAllTags)
      .catch(() => {/* ignore */});
  }, []);

  function handleSearchChange(value: string): void {
    setSearchValue(value);
    setPage(1);
  }

  function handlePageSizeChange(value: number): void {
    setPageSizeValue(value);
    setPage(1);
  }

  function handleTagsChange(tags: string[]): void {
    setSelectedTags(tags);
    setPage(1);
  }

  async function handleDuplicate(e: React.MouseEvent, configId: string) {
    e.preventDefault();
    setDuplicatingId(configId);
    try {
      await duplicateConfig(configId);
      await loadConfigs();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to duplicate config');
    } finally {
      setDuplicatingId(null);
    }
  }

  if (loading && configs.length === 0 && total === 0 && !search && selectedTags.length === 0) {
    return <LoadingSkeleton rows={4} />;
  }
  if (error) return <Alert variant="destructive" className="animate-fade-in"><AlertDescription>{error}</AlertDescription></Alert>;

  return (
    <PageTransition>
      <PageHeader
        title="Eval Configs"
        description="Manage your evaluation configurations"
        action={
          <Link to="/configs/new">
            <Button size="sm"><Plus className="mr-2 h-4 w-4" />New Config</Button>
          </Link>
        }
      />

      <ListControls
        search={search}
        page={page}
        pageSize={pageSize}
        pages={pages}
        total={total}
        itemLabel="configs"
        onSearchChange={handleSearchChange}
        onPageChange={setPage}
        onPageSizeChange={handlePageSizeChange}
      />

      <TagFilter allTags={allTags} selectedTags={selectedTags} onChange={handleTagsChange} />

      {configs.length === 0 ? (
        <Card className="p-12 text-center animate-scale-in">
          <p className="text-foreground-secondary text-base">
            {search || selectedTags.length > 0 ? 'No configs match your filters.' : 'No configs yet.'}
          </p>
          {!search && selectedTags.length === 0 && (
            <Link to="/configs/new">
              <Button className="mt-4" size="sm">Create your first config</Button>
            </Link>
          )}
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {configs.map((config, idx) => (
            <Link key={config.id} to={`/configs/${config.id}`}>
              <Card
                className="p-4 h-full hover:bg-background-hover hover:border-border-hover hover:shadow-medium transition-all duration-200 ease-[var(--ease-smooth)] animate-fade-in-up"
                style={{ animationDelay: `${idx * 60}ms` }}
              >
                <h3 className="text-sm font-medium text-foreground flex items-center gap-1.5">
                  {config.readonly && <Lock className="h-3 w-3 text-warning shrink-0" />}
                  {config.name}
                </h3>
                <p className="text-xs text-foreground-secondary mt-1 line-clamp-2">{config.system_prompt}</p>
                <div className="flex items-center gap-2 mt-3">
                  <Badge>{config.model}</Badge>
                  {config.graders && config.graders.length > 0 && (
                    <Badge>{config.graders.length} grader{config.graders.length !== 1 ? 's' : ''}</Badge>
                  )}
                </div>
                {config.tags && config.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {config.tags.map((tag: string) => (
                      <Badge key={tag} variant="info" className="text-[10px] px-1.5 py-0">{tag}</Badge>
                    ))}
                  </div>
                )}
                <div className="flex items-center justify-between mt-2">
                  <p className="text-xs text-foreground-disabled">{formatDate(config.created_at)}</p>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0"
                    disabled={duplicatingId === config.id}
                    onClick={(e) => handleDuplicate(e, config.id)}
                    title="Duplicate config"
                  >
                    <Copy className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </PageTransition>
  );
}
