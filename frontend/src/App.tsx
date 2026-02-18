import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppLayout } from '@/components/AppLayout';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { Dashboard } from '@/pages/Dashboard';
import { ConfigList } from '@/pages/configs/ConfigList';
import { ConfigNew } from '@/pages/configs/ConfigNew';
import { ConfigDetail } from '@/pages/configs/ConfigDetail';
import { ConfigEdit } from '@/pages/configs/ConfigEdit';
import { DatasetList } from '@/pages/datasets/DatasetList';
import { DatasetNew } from '@/pages/datasets/DatasetNew';
import { DatasetDetail } from '@/pages/datasets/DatasetDetail';
import { RunList } from '@/pages/runs/RunList';
import { RunNew } from '@/pages/runs/RunNew';
import { RunDetail } from '@/pages/runs/RunDetail';
import { RunCompare } from '@/pages/runs/RunCompare';
import { VectorStoreList } from '@/pages/vector-stores/VectorStoreList';
import { VectorStoreNew } from '@/pages/vector-stores/VectorStoreNew';
import { VectorStoreDetail } from '@/pages/vector-stores/VectorStoreDetail';

export function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/configs" element={<ConfigList />} />
            <Route path="/configs/new" element={<ConfigNew />} />
            <Route path="/configs/:id" element={<ConfigDetail />} />
            <Route path="/configs/:id/edit" element={<ConfigEdit />} />
            <Route path="/datasets" element={<DatasetList />} />
            <Route path="/datasets/new" element={<DatasetNew />} />
            <Route path="/datasets/:id" element={<DatasetDetail />} />
            <Route path="/runs" element={<RunList />} />
            <Route path="/runs/new" element={<RunNew />} />
            <Route path="/runs/compare" element={<RunCompare />} />
            <Route path="/runs/:id" element={<RunDetail />} />
            <Route path="/vector-stores" element={<VectorStoreList />} />
            <Route path="/vector-stores/new" element={<VectorStoreNew />} />
            <Route path="/vector-stores/:id" element={<VectorStoreDetail />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
