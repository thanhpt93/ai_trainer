export type TaskType =
  | 'Image Classification'
  | 'Object Detection'
  | 'Image Segmentation'
  | 'OCR'
  | 'Anomaly Detection'
  | 'Keypoint Detection'
  | 'Image Similarity';

export const TASK_TYPES: TaskType[] = [
  'Image Classification',
  'Object Detection',
  'Image Segmentation',
  'OCR',
  'Anomaly Detection',
  'Keypoint Detection',
  'Image Similarity',
];

export interface Project {
  id: string;
  name: string;
  description?: string | null;
  task_type: TaskType;
  root_path: string;
  is_multi_label: boolean;
  allow_negative_images: boolean;
  created_at: string;
  updated_at: string;
  schema_version: number;
  dataset_count?: number;
}

export interface ProjectCreate {
  name: string;
  description?: string;
  task_type: TaskType;
  root_path?: string;
  is_multi_label?: boolean;
  allow_negative_images?: boolean;
}

export interface ProjectUpdate {
  name?: string;
  description?: string;
  task_type?: TaskType;
  root_path?: string;
  is_multi_label?: boolean;
  allow_negative_images?: boolean;
}

export interface ProjectLabel {
  id: string;
  project_id: string;
  name: string;
  color: string;
  description?: string | null;
  annotation_count: number;
  created_at: string;
  updated_at: string;
}

export interface LabelCreate {
  name: string;
  color?: string;
  description?: string;
}

export interface LabelUpdate {
  name?: string;
  color?: string;
  description?: string;
}

export type DatasetFormat = 'folder_images' | 'coco' | 'yolo' | 'pascal_voc';

export interface Dataset {
  id: string;
  project_id: string;
  name: string;
  description?: string | null;
  root_path: string;
  format: DatasetFormat;
  image_count: number;
  annotation_count: number;
  valid_image_count: number;
  corrupted_image_count: number;
  unsupported_file_count: number;
  is_linked: boolean;
  last_scanned_at?: string | null;
  created_at: string;
  updated_at: string;
  schema_version: number;
}

export interface DatasetCreate {
  name: string;
  description?: string;
  root_path: string;
  format?: DatasetFormat;
  is_linked?: boolean;
  scan_immediately?: boolean;
}

export interface DatasetUpdate {
  name?: string;
  description?: string;
}

export interface DatasetScanResult {
  dataset_id: string;
  scanned_files: number;
  valid_images: number;
  corrupted_images: number;
  unsupported_files: number;
  duration_seconds: number;
  message: string;
}

export interface ImageRecord {
  id: string;
  dataset_id: string;
  relative_path: string;
  absolute_path: string;
  file_size_bytes: number;
  width?: number | null;
  height?: number | null;
  channels?: number | null;
  format?: string | null;
  is_valid: boolean;
  error_reason?: string | null;
  created_at: string;
}

export interface PaginatedImages {
  items: ImageRecord[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// Phase 2: Annotation Types
export type AnnotationStatus = 'UNANNOTATED' | 'ANNOTATED' | 'NEEDS_REVIEW' | 'INVALID';

export type AnnotationTool = 'select' | 'draw' | 'pan';

export interface BoundingBox {
  id: string;
  label_id: string;
  label_name: string;
  label_color: string;
  x_min: number; // normalized [0, 1]
  y_min: number; // normalized [0, 1]
  x_max: number; // normalized [0, 1]
  y_max: number; // normalized [0, 1]
  confidence: number;
}

export interface BoundingBoxCreate {
  label_id: string;
  x_min: number;
  y_min: number;
  x_max: number;
  y_max: number;
  confidence?: number;
}

export interface ImageAnnotation {
  id: string;
  dataset_id: string;
  image_id: string;
  task_type: string;
  status: AnnotationStatus;
  is_negative: boolean;
  label_ids: string[];
  labels: ProjectLabel[];
  objects: BoundingBox[];
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ImageAnnotationSaveRequest {
  task_type: TaskType;
  is_negative?: boolean;
  status?: AnnotationStatus;
  label_ids?: string[];
  objects?: BoundingBoxCreate[];
  notes?: string;
}

export interface DatasetAnnotationSummary {
  dataset_id: string;
  total_images: number;
  annotated_images: number;
  unannotated_images: number;
  needs_review_images: number;
  invalid_images: number;
  completion_percentage: number;
  class_distribution: Record<string, number>;
}

export interface AnnotatedImageItem {
  id: string;
  dataset_id: string;
  relative_path: string;
  file_size_bytes: number;
  width?: number | null;
  height?: number | null;
  is_valid: boolean;
  status: AnnotationStatus;
  is_negative: boolean;
  annotation_count: number;
  assigned_labels: string[];
  notes?: string | null;
  updated_at?: string | null;
}

export interface PaginatedAnnotatedImages {
  items: AnnotatedImageItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export type ExportFormat = 'yolo' | 'coco' | 'pascal_voc' | 'csv' | 'json';

export interface ExportRequest {
  format: ExportFormat;
  output_dir?: string;
  include_unannotated?: boolean;
}

export interface ExportResponse {
  export_path: string;
  format: string;
  total_exported: number;
  message: string;
}

export interface DashboardStats {
  total_projects: number;
  total_datasets: number;
  total_indexed_images: number;
  running_training_jobs: number;
  recent_projects: Project[];
}

export interface SystemInfo {
  os: string;
  python_version: string;
  cpu_count: number;
  memory_total_gb?: number | null;
  memory_available_gb?: number | null;
  cuda_available: boolean;
  cuda_device_name?: string | null;
  app_data_dir: string;
  database_path: string;
}

export interface HealthStatus {
  status: string;
  app_name: string;
  version: string;
  database_connected: boolean;
  app_data_dir: string;
}

export interface PathValidationResult {
  is_valid: boolean;
  resolved_path: string;
  exists: boolean;
  is_directory: boolean;
  is_readable: boolean;
  error_message?: string | null;
  subdirectories: string[];
  estimated_image_count: number;
}

// Phase 3 & 4: Hardware, Training & Model Registry Types
export interface CUDADeviceInfo {
  index: number;
  name: string;
  total_memory_mb: number;
  free_memory_mb: number;
  compute_capability: string;
}

export interface HardwareInfo {
  os: string;
  python_version: string;
  pytorch_version: string;
  cpu_count_logical: number;
  cpu_count_physical?: number | null;
  system_memory_total_gb: number;
  system_memory_available_gb: number;
  cuda_available: boolean;
  cuda_version?: string | null;
  gpu_devices: CUDADeviceInfo[];
  recommended_device: string;
  available_devices: string[];
}

export interface ModelCatalogItem {
  id: string;
  name: string;
  architecture: string;
  task_type: string;
  description: string;
  supported_input_sizes: number[];
  default_input_size: number;
  parameters_count_million: number;
  pretrained_available: boolean;
  supported_devices: string[];
  default_learning_rate: number;
  default_batch_size: number;
  export_formats: string[];
}

export interface SplitConfig {
  train_ratio: number;
  val_ratio: number;
  test_ratio: number;
  random_seed: number;
  stratified: boolean;
}

export interface TrainingHyperparameters {
  model_architecture: string;
  pretrained: boolean;
  device: string;
  input_size: number;
  batch_size: number;
  epochs: number;
  learning_rate: number;
  optimizer: 'AdamW' | 'SGD';
  weight_decay: number;
  momentum: number;
  scheduler: 'step' | 'cosine' | 'none';
  early_stopping: boolean;
  patience: number;
  num_workers: number;
  horizontal_flip: boolean;
  rotation_degrees: number;
  color_jitter: boolean;
  // Object Detection fields
  confidence_threshold?: number;
  iou_threshold?: number;
  max_detections?: number;
  min_size?: number;
  max_size?: number;
  grad_clip?: number;
}

export interface ClassItem {
  index: number;
  label_id: string;
  name: string;
  color: string;
  count: number;
}

export interface DatasetValidationResponse {
  is_valid: boolean;
  project_id: string;
  dataset_id: string;
  task_type?: string;
  total_images: number;
  valid_annotated_images: number;
  unannotated_images: number;
  invalid_annotations: number;
  negative_images: number;
  missing_files: number;
  classes: ClassItem[];
  class_imbalance_warning: boolean;
  train_count: number;
  val_count: number;
  test_count: number;
  split_manifest_id?: string | null;
  total_bounding_boxes?: number;
  boxes_per_class?: Record<string, number>;
  images_per_class?: Record<string, number>;
  errors: string[];
  warnings: string[];
}

export interface DatasetValidationRequest {
  project_id: string;
  dataset_id: string;
  split_config?: SplitConfig;
}

export type TrainingJobStatus =
  | 'QUEUED'
  | 'PREPARING'
  | 'RUNNING'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCEL_REQUESTED'
  | 'CANCELLED';

export interface TrainingJob {
  id: string;
  name?: string | null;
  project_id: string;
  dataset_id: string;
  task_type: string;
  model_id?: string | null;
  model_architecture?: string | null;
  device?: string | null;
  status: TrainingJobStatus;
  current_epoch: number;
  total_epochs: number;
  best_metric_name?: string | null;
  best_metric_value?: number | null;
  checkpoint_dir?: string | null;
  log_file_path?: string | null;
  configuration_json?: string | null;
  metrics_json?: string | null;
  evaluation_json?: string | null;
  pid?: number | null;
  is_cancelled: boolean;
  started_at?: string | null;
  completed_at?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface TrainingJobCreate {
  project_id: string;
  dataset_id: string;
  name?: string;
  hyperparameters: TrainingHyperparameters;
  split_config?: SplitConfig;
}

export interface EpochMetric {
  epoch: number;
  train_loss: number;
  train_accuracy?: number | null;
  val_loss?: number | null;
  val_accuracy?: number | null;
  val_precision?: number | null;
  val_recall?: number | null;
  val_f1?: number | null;
  learning_rate: number;
  duration_seconds: number;
  timestamp: string;
  // Object Detection epoch metrics
  val_map?: number | null;
  val_map_50?: number | null;
  val_map_75?: number | null;
  loss_classifier?: number | null;
  loss_box_reg?: number | null;
  loss_objectness?: number | null;
  loss_rpn_box_reg?: number | null;
}

export interface ConfusionMatrixData {
  labels: string[];
  matrix: number[][];
}

export interface PerClassMetric {
  class_name: string;
  precision: number;
  recall: number;
  f1_score: number;
  support: number;
}

export interface MisclassifiedImage {
  image_id: string;
  relative_path: string;
  ground_truth: string;
  predicted: string;
  confidence: number;
}

export interface EvaluationReport {
  total_samples: number;
  accuracy: number;
  precision_macro: number;
  recall_macro: number;
  f1_macro: number;
  per_class_metrics: PerClassMetric[];
  confusion_matrix: ConfusionMatrixData;
  misclassified_samples: MisclassifiedImage[];
  evaluated_split?: string;
  evaluated_at: string;
}

export interface DetectedObject {
  label_id?: string | null;
  class_name: string;
  class_index: number;
  confidence: number;
  box: [number, number, number, number]; // [x1, y1, x2, y2]
  box_normalized: [number, number, number, number]; // [x_min, y_min, x_max, y_max]
  matched_gt?: boolean | null;
  iou?: number | null;
}

export interface DetectionSampleVisual {
  image_id: string;
  relative_path: string;
  width: number;
  height: number;
  ground_truth_boxes: DetectedObject[];
  predicted_boxes: DetectedObject[];
  matched_count: number;
  false_positive_count: number;
  false_negative_count: number;
}

export interface PerClassDetectionMetric {
  class_name: string;
  ap: number;
  ap50: number;
  ap75: number;
  precision: number;
  recall: number;
  ground_truth_count: number;
  prediction_count: number;
}

export interface DetectionEvaluationReport {
  task_type: string;
  total_samples: number;
  total_ground_truth_boxes: number;
  total_predicted_boxes: number;
  map: number;
  map_50: number;
  map_75: number;
  precision: number;
  recall: number;
  per_class_metrics: PerClassDetectionMetric[];
  samples: DetectionSampleVisual[];
  operating_point: {
    confidence_threshold: number;
    iou_threshold: number;
  };
  evaluated_split?: string;
  evaluated_at: string;
}

export interface ClassProbability {
  class_name: string;
  probability: number;
}

export interface PredictRequest {
  image_path?: string;
  image_base64?: string;
  confidence_threshold?: number;
  iou_threshold?: number;
}

export interface PredictResponse {
  predicted_class?: string;
  confidence?: number;
  top_probabilities?: ClassProbability[];
  inference_time_ms: number;
  device: string;
  model_architecture: string;
  task_type?: string;
  detected_objects?: DetectedObject[];
  image_width?: number | null;
  image_height?: number | null;
}

export interface ModelArtifact {
  id: string;
  name: string;
  task_type: string;
  version: string;
  artifact_path: string;
  framework: string;
  export_format: string;
  metadata_path?: string | null;
  project_id?: string | null;
  dataset_id?: string | null;
  training_job_id?: string | null;
  model_architecture?: string | null;
  metrics_summary_json?: string | null;
  checksum_sha256?: string | null;
  file_size_bytes: number;
  is_exported: boolean;
  created_at: string;
}

export interface ExportModelRequest {
  format?: string;
  input_size?: number;
  dynamic_batch?: boolean;
}

export interface ExportModelResponse {
  success: boolean;
  artifact_id: string;
  model_name: string;
  export_dir: string;
  onnx_file_path: string;
  manifest_path: string;
  metadata_path: string;
  checksum_sha256: string;
  file_size_bytes: number;
  verified_with_inference: boolean;
  error?: string | null;
}

declare global {
  interface Window {
    electronAPI?: {
      getBackendUrl: () => Promise<string>;
      selectDirectory: (defaultPath?: string) => Promise<string | null>;
      getAppVersion: () => Promise<string>;
      isElectron?: boolean;
    };
  }
}
