import React from 'react';
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from './layouts/AppLayout';
import { DashboardPage } from './pages/DashboardPage';
import { ProjectsPage } from './pages/ProjectsPage';
import { ProjectDetailPage } from './pages/ProjectDetailPage';
import { DatasetsPage } from './pages/DatasetsPage';
import { DatasetDetailPage } from './pages/DatasetDetailPage';
import { SettingsPage } from './pages/SettingsPage';
import { AnnotationWorkspace } from './features/annotation/components/AnnotationWorkspace';
import { TrainingPage } from './pages/TrainingPage';
import { TrainingMonitorPage } from './pages/TrainingMonitorPage';
import { ExperimentsPage } from './pages/ExperimentsPage';
import { EvaluationPage } from './pages/EvaluationPage';
import { ModelRegistryPage } from './pages/ModelRegistryPage';

export const App: React.FC = () => {
  return (
    <HashRouter>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          
          {/* Projects */}
          <Route path="projects" element={<ProjectsPage />} />
          <Route path="projects/:id" element={<ProjectDetailPage />} />

          {/* Datasets */}
          <Route path="datasets" element={<DatasetsPage />} />
          <Route path="datasets/:id" element={<DatasetDetailPage />} />

          {/* Phase 2: Annotation Studio */}
          <Route path="annotation" element={<AnnotationWorkspace />} />

          {/* Phase 3: Models & Training Engine */}
          <Route path="training" element={<TrainingPage />} />
          <Route path="training/:id" element={<TrainingMonitorPage />} />

          {/* Experiments */}
          <Route path="experiments" element={<ExperimentsPage />} />

          {/* Evaluation & Benchmark */}
          <Route path="evaluation" element={<EvaluationPage />} />

          {/* Model Registry & Export */}
          <Route path="models" element={<ModelRegistryPage />} />

          {/* Settings */}
          <Route path="settings" element={<SettingsPage />} />

          {/* Catch-all redirect to Dashboard */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </HashRouter>
  );
};
