import {
  Project,
  ProjectCreate,
  ProjectUpdate,
  ProjectLabel,
  LabelCreate,
  LabelUpdate,
  Dataset,
  DatasetCreate,
  DatasetUpdate,
  DatasetScanResult,
  PaginatedImages,
  ImageAnnotation,
  ImageAnnotationSaveRequest,
  DatasetAnnotationSummary,
  PaginatedAnnotatedImages,
  ExportRequest,
  ExportResponse,
  DashboardStats,
  SystemInfo,
  HealthStatus,
  PathValidationResult,
  HardwareInfo,
  ModelCatalogItem,
  DatasetValidationRequest,
  DatasetValidationResponse,
  TrainingJob,
  TrainingJobCreate,
  EpochMetric,
  EvaluationReport,
  ModelArtifact,
  ExportModelRequest,
  ExportModelResponse,
} from '../types';

let cachedBackendUrl: string | null = null;

export async function getBackendBaseUrl(): Promise<string> {
  if (cachedBackendUrl) return cachedBackendUrl;

  if (window.electronAPI?.getBackendUrl) {
    try {
      cachedBackendUrl = await window.electronAPI.getBackendUrl();
      return cachedBackendUrl;
    } catch (e) {
      console.warn('Failed to get backend URL from Electron, using default:', e);
    }
  }
  cachedBackendUrl = 'http://127.0.0.1:8000';
  return cachedBackendUrl;
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const baseUrl = await getBackendBaseUrl();
  const url = `${baseUrl}/api/v1${endpoint}`;

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = response.statusText;
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errorDetail;
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const api = {
  // Health & System
  async checkHealth(): Promise<HealthStatus> {
    return request<HealthStatus>('/health');
  },

  async getSystemInfo(): Promise<SystemInfo> {
    return request<SystemInfo>('/system-info');
  },

  async getHardwareInfo(): Promise<HardwareInfo> {
    return request<HardwareInfo>('/system/hardware');
  },

  async getDashboardStats(): Promise<DashboardStats> {
    return request<DashboardStats>('/dashboard/stats');
  },

  // Projects
  async getProjects(search?: string, task_type?: string): Promise<{ items: Project[]; total: number }> {
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (task_type) params.append('task_type', task_type);
    const query = params.toString() ? `?${params.toString()}` : '';
    return request<{ items: Project[]; total: number }>(`/projects${query}`);
  },

  async getProject(id: string): Promise<Project> {
    return request<Project>(`/projects/${id}`);
  },

  async createProject(data: ProjectCreate): Promise<Project> {
    return request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateProject(id: string, data: ProjectUpdate): Promise<Project> {
    return request<Project>(`/projects/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  async deleteProject(id: string): Promise<void> {
    await request<void>(`/projects/${id}`, {
      method: 'DELETE',
    });
  },

  // Labels (Phase 2)
  async getProjectLabels(projectId: string): Promise<{ items: ProjectLabel[]; total: number }> {
    return request<{ items: ProjectLabel[]; total: number }>(`/projects/${projectId}/labels`);
  },

  async createProjectLabel(projectId: string, data: LabelCreate): Promise<ProjectLabel> {
    return request<ProjectLabel>(`/projects/${projectId}/labels`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateProjectLabel(labelId: string, data: LabelUpdate): Promise<ProjectLabel> {
    return request<ProjectLabel>(`/labels/${labelId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  async deleteProjectLabel(labelId: string): Promise<void> {
    await request<void>(`/labels/${labelId}`, {
      method: 'DELETE',
    });
  },

  // Datasets
  async getProjectDatasets(projectId: string): Promise<{ items: Dataset[]; total: number }> {
    return request<{ items: Dataset[]; total: number }>(`/projects/${projectId}/datasets`);
  },

  async createDataset(projectId: string, data: DatasetCreate): Promise<Dataset> {
    return request<Dataset>(`/projects/${projectId}/datasets`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async getAllDatasets(): Promise<{ items: Dataset[]; total: number }> {
    return request<{ items: Dataset[]; total: number }>('/datasets');
  },

  async getDataset(id: string): Promise<Dataset> {
    return request<Dataset>(`/datasets/${id}`);
  },

  async updateDataset(id: string, data: DatasetUpdate): Promise<Dataset> {
    return request<Dataset>(`/datasets/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  async deleteDataset(id: string): Promise<void> {
    await request<void>(`/datasets/${id}`, {
      method: 'DELETE',
    });
  },

  async scanDataset(id: string): Promise<DatasetScanResult> {
    return request<DatasetScanResult>(`/datasets/${id}/scan`, {
      method: 'POST',
    });
  },

  async getDatasetImages(
    id: string,
    isValid?: boolean,
    page: number = 1,
    pageSize: number = 50
  ): Promise<PaginatedImages> {
    const params = new URLSearchParams();
    if (isValid !== undefined) params.append('is_valid', String(isValid));
    params.append('page', String(page));
    params.append('page_size', String(pageSize));
    return request<PaginatedImages>(`/datasets/${id}/images?${params.toString()}`);
  },

  async getImageFileUrl(datasetId: string, imageId: string): Promise<string> {
    const baseUrl = await getBackendBaseUrl();
    return `${baseUrl}/api/v1/datasets/${datasetId}/images/${imageId}/file`;
  },

  // Annotation Studio (Phase 2)
  async getDatasetAnnotationSummary(datasetId: string): Promise<DatasetAnnotationSummary> {
    return request<DatasetAnnotationSummary>(`/datasets/${datasetId}/annotation-summary`);
  },

  async getAnnotatedImages(
    datasetId: string,
    statusFilter?: string,
    search?: string,
    page: number = 1,
    pageSize: number = 50
  ): Promise<PaginatedAnnotatedImages> {
    const params = new URLSearchParams();
    if (statusFilter) params.append('status', statusFilter);
    if (search) params.append('search', search);
    params.append('page', String(page));
    params.append('page_size', String(pageSize));
    return request<PaginatedAnnotatedImages>(`/datasets/${datasetId}/annotated-images?${params.toString()}`);
  },

  async getImageAnnotation(imageId: string): Promise<ImageAnnotation> {
    return request<ImageAnnotation>(`/images/${imageId}/annotation`);
  },

  async saveImageAnnotation(imageId: string, data: ImageAnnotationSaveRequest): Promise<ImageAnnotation> {
    return request<ImageAnnotation>(`/images/${imageId}/annotation`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async markImageNegative(imageId: string, isNegative: boolean): Promise<ImageAnnotation> {
    return request<ImageAnnotation>(`/images/${imageId}/annotation/mark-negative`, {
      method: 'POST',
      body: JSON.stringify({ is_negative: isNegative }),
    });
  },

  async markImageReview(imageId: string, needsReview: boolean): Promise<ImageAnnotation> {
    return request<ImageAnnotation>(`/images/${imageId}/annotation/mark-review`, {
      method: 'POST',
      body: JSON.stringify({ needs_review: needsReview }),
    });
  },

  async exportDataset(datasetId: string, data: ExportRequest): Promise<ExportResponse> {
    return request<ExportResponse>(`/datasets/${datasetId}/export`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // Phase 3: Training & Model APIs
  async getAvailableModels(): Promise<ModelCatalogItem[]> {
    return request<ModelCatalogItem[]>('/training/models');
  },

  async validateTrainingDataset(data: DatasetValidationRequest): Promise<DatasetValidationResponse> {
    return request<DatasetValidationResponse>('/training/datasets/validate', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async getTrainingJobs(projectId?: string, limit: number = 50): Promise<TrainingJob[]> {
    const params = new URLSearchParams();
    if (projectId) params.append('project_id', projectId);
    params.append('limit', String(limit));
    return request<TrainingJob[]>(`/training/jobs?${params.toString()}`);
  },

  async createTrainingJob(data: TrainingJobCreate): Promise<TrainingJob> {
    return request<TrainingJob>('/training/jobs', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async getTrainingJob(id: string): Promise<TrainingJob> {
    return request<TrainingJob>(`/training/jobs/${id}`);
  },

  async startTrainingJob(id: string): Promise<TrainingJob> {
    return request<TrainingJob>(`/training/jobs/${id}/start`, {
      method: 'POST',
    });
  },

  async cancelTrainingJob(id: string): Promise<TrainingJob> {
    return request<TrainingJob>(`/training/jobs/${id}/cancel`, {
      method: 'POST',
    });
  },

  async getTrainingJobLogs(id: string, tail: number = 200): Promise<{ job_id: string; logs: string[]; total_lines: number }> {
    return request<{ job_id: string; logs: string[]; total_lines: number }>(`/training/jobs/${id}/logs?tail=${tail}`);
  },

  async getTrainingJobMetrics(id: string): Promise<EpochMetric[]> {
    return request<EpochMetric[]>(`/training/jobs/${id}/metrics`);
  },

  async getTrainingJobEvaluations(id: string): Promise<EvaluationReport | any> {
    return request<EvaluationReport | any>(`/training/jobs/${id}/evaluations`);
  },

  async exportTrainingJobModel(id: string, data: ExportModelRequest): Promise<ExportModelResponse> {
    return request<ExportModelResponse>(`/training/jobs/${id}/export`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // Model Registry
  async getRegisteredModels(projectId?: string): Promise<ModelArtifact[]> {
    const params = new URLSearchParams();
    if (projectId) params.append('project_id', projectId);
    const query = params.toString() ? `?${params.toString()}` : '';
    return request<ModelArtifact[]>(`/models${query}`);
  },

  async getRegisteredModel(id: string): Promise<ModelArtifact> {
    return request<ModelArtifact>(`/models/${id}`);
  },

  async deleteRegisteredModel(id: string): Promise<void> {
    await request<void>(`/models/${id}`, {
      method: 'DELETE',
    });
  },

  // Filesystem Helper
  async validatePath(path: string): Promise<PathValidationResult> {
    return request<PathValidationResult>('/filesystem/validate-path', {
      method: 'POST',
      body: JSON.stringify({ path }),
    });
  },
};
