import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Play,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Cpu,
  Layers,
  Settings2,
  RefreshCw,
  FolderKanban,
  Activity,
  Boxes,
  Database,
  Sliders,
  ChevronRight,
  ShieldAlert,
  Crosshair,
} from 'lucide-react';
import { api } from '../services/api';
import {
  Project,
  Dataset,
  ModelCatalogItem,
  HardwareInfo,
  DatasetValidationResponse,
  TrainingJob,
  TrainingHyperparameters,
  SplitConfig,
} from '../types';

export const TrainingPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Tab: 'wizard' (Start New Run) or 'jobs' (Recent Runs)
  const [activeTab, setActiveTab] = useState<'wizard' | 'jobs'>(
    searchParams.get('tab') === 'jobs' ? 'jobs' : 'wizard'
  );

  // Data
  const [projects, setProjects] = useState<Project[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [models, setModels] = useState<ModelCatalogItem[]>([]);
  const [hardware, setHardware] = useState<HardwareInfo | null>(null);
  const [jobs, setJobs] = useState<TrainingJob[]>([]);

  // Selection
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>('');
  const [selectedModelId, setSelectedModelId] = useState<string>('');
  const [runName, setRunName] = useState<string>('');

  // Hyperparameters
  const [hyperparams, setHyperparams] = useState<TrainingHyperparameters>({
    model_architecture: 'resnet18',
    pretrained: true,
    device: 'auto',
    input_size: 224,
    batch_size: 16,
    epochs: 10,
    learning_rate: 0.001,
    optimizer: 'AdamW',
    weight_decay: 0.0001,
    momentum: 0.9,
    scheduler: 'step',
    early_stopping: false,
    patience: 5,
    num_workers: 0,
    horizontal_flip: true,
    rotation_degrees: 10,
    color_jitter: false,
    confidence_threshold: 0.5,
    iou_threshold: 0.5,
    max_detections: 100,
  });

  // Split Configuration
  const [splitConfig, setSplitConfig] = useState<SplitConfig>({
    train_ratio: 0.8,
    val_ratio: 0.1,
    test_ratio: 0.1,
    random_seed: 42,
    stratified: true,
  });

  // Validation state
  const [validating, setValidating] = useState<boolean>(false);
  const [validationResult, setValidationResult] = useState<DatasetValidationResponse | null>(null);
  const [startingJob, setStartingJob] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const selectedProject = projects.find((p) => p.id === selectedProjectId);
  const isDetection = selectedProject ? selectedProject.task_type.includes('Detection') : false;

  // 1. Initial Load: Projects, Models, Hardware, Jobs
  useEffect(() => {
    const initData = async () => {
      try {
        const [projRes, modelRes, hwRes, jobsRes] = await Promise.all([
          api.getProjects(),
          api.getAvailableModels(),
          api.getHardwareInfo(),
          api.getTrainingJobs(),
        ]);

        setProjects(projRes.items);
        setModels(modelRes);
        setHardware(hwRes);
        setJobs(jobsRes);

        const paramProj = searchParams.get('project');
        const activeProj = paramProj || (projRes.items.length > 0 ? projRes.items[0].id : '');
        setSelectedProjectId(activeProj);

        if (activeProj) {
          const dsRes = await api.getProjectDatasets(activeProj);
          setDatasets(dsRes.items);
          if (dsRes.items.length > 0) {
            setSelectedDatasetId(dsRes.items[0].id);
          }
        }
      } catch (err: any) {
        setErrorMsg(err.message || 'Failed to initialize training data');
      }
    };
    initData();
  }, []);

  // 2. When Project Changes: Reload datasets and adapt models
  useEffect(() => {
    if (!selectedProjectId) return;
    const proj = projects.find((p) => p.id === selectedProjectId);
    const projIsDet = proj ? proj.task_type.includes('Detection') : false;

    // Filter models
    const compatibleModels = models.filter((m) =>
      projIsDet ? m.task_type.includes('Detection') : m.task_type.includes('Classification')
    );

    if (compatibleModels.length > 0) {
      const defaultM = compatibleModels[0];
      setSelectedModelId(defaultM.id);
      setHyperparams((prev) => ({
        ...prev,
        model_architecture: defaultM.architecture,
        input_size: defaultM.default_input_size,
        learning_rate: defaultM.default_learning_rate,
        batch_size: defaultM.default_batch_size,
      }));
    }

    const loadDatasets = async () => {
      try {
        const dsRes = await api.getProjectDatasets(selectedProjectId);
        setDatasets(dsRes.items);
        if (dsRes.items.length > 0) {
          setSelectedDatasetId(dsRes.items[0].id);
        } else {
          setSelectedDatasetId('');
          setValidationResult(null);
        }
      } catch (err: any) {
        console.error('Failed to load project datasets:', err);
      }
    };
    loadDatasets();
  }, [selectedProjectId, projects, models]);

  // 3. When Dataset Changes or Split Config changes: Run Dataset Validation
  useEffect(() => {
    if (!selectedProjectId || !selectedDatasetId) {
      setValidationResult(null);
      return;
    }

    const runValidation = async () => {
      setValidating(true);
      try {
        const res = await api.validateTrainingDataset({
          project_id: selectedProjectId,
          dataset_id: selectedDatasetId,
          split_config: splitConfig,
        });
        setValidationResult(res);
      } catch (err: any) {
        console.error('Validation request error:', err);
      } finally {
        setValidating(false);
      }
    };

    runValidation();
  }, [selectedProjectId, selectedDatasetId, splitConfig]);

  // Handle Model Selection
  const handleSelectModel = (model: ModelCatalogItem) => {
    setSelectedModelId(model.id);
    setHyperparams((prev) => ({
      ...prev,
      model_architecture: model.architecture,
      input_size: model.default_input_size,
      learning_rate: model.default_learning_rate,
      batch_size: model.default_batch_size,
    }));
  };

  // Launch Training Job
  const handleStartTraining = async () => {
    if (!validationResult?.is_valid) return;
    setStartingJob(true);
    setErrorMsg(null);

    try {
      const job = await api.createTrainingJob({
        project_id: selectedProjectId,
        dataset_id: selectedDatasetId,
        name: runName.trim() || undefined,
        hyperparameters: {
          ...hyperparams,
          model_architecture: selectedModelId,
        },
        split_config: splitConfig,
      });

      // Start the job immediately
      await api.startTrainingJob(job.id);
      navigate(`/training/${job.id}`);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to start training job');
      setStartingJob(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'RUNNING':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 animate-pulse">
            <RefreshCw className="w-3 h-3 animate-spin" /> Running
          </span>
        );
      case 'PREPARING':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/20 text-blue-400 border border-blue-500/30">
            <RefreshCw className="w-3 h-3 animate-spin" /> Preparing
          </span>
        );
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
            <CheckCircle2 className="w-3 h-3" /> Completed
          </span>
        );
      case 'CANCELLED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-400 border border-amber-500/30">
            <AlertTriangle className="w-3 h-3" /> Cancelled
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/20 text-rose-400 border border-rose-500/30">
            <XCircle className="w-3 h-3" /> Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-500/20 text-slate-400 border border-slate-500/30">
            {status}
          </span>
        );
    }
  };

  const filteredModels = models.filter((m) =>
    isDetection ? m.task_type.includes('Detection') : m.task_type.includes('Classification')
  );

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-950 overflow-y-auto">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/60 backdrop-blur px-8 py-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                {isDetection ? 'Object Detection Engine' : 'Classification Engine'}
              </span>
              <h1 className="text-xl font-bold text-white tracking-tight">
                {isDetection ? 'Object Detection Training' : 'Image Classification Training'}
              </h1>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              End-to-end PyTorch training pipeline with worker process isolation, real-time metrics, evaluation benchmark, and ONNX deployment export.
            </p>
          </div>

          {/* Navigation Tabs */}
          <div className="flex bg-slate-800/80 p-1 rounded-lg border border-slate-700/60 self-start md:self-auto">
            <button
              onClick={() => setActiveTab('wizard')}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition ${
                activeTab === 'wizard'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Play className="w-3.5 h-3.5" /> Start New Run
            </button>
            <button
              onClick={() => setActiveTab('jobs')}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition ${
                activeTab === 'jobs'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Activity className="w-3.5 h-3.5" /> Experiment Jobs ({jobs.length})
            </button>
          </div>
        </div>

        {/* Hardware Status Strip */}
        {hardware && (
          <div className="mt-4 flex flex-wrap items-center gap-4 text-xs bg-slate-950/60 px-3 py-2 rounded-lg border border-slate-800/80 text-slate-300">
            <div className="flex items-center gap-1.5">
              <Cpu className="w-4 h-4 text-indigo-400" />
              <span>CPU: {hardware.cpu_count_logical} Logical Cores</span>
            </div>
            <div className="w-px h-3 bg-slate-800" />
            <div>RAM: {hardware.system_memory_available_gb} GB Free / {hardware.system_memory_total_gb} GB Total</div>
            <div className="w-px h-3 bg-slate-800" />
            <div className="flex items-center gap-1.5">
              {hardware.cuda_available ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-emerald-400 font-medium">
                    GPU Ready: {hardware.gpu_devices[0]?.name || 'NVIDIA CUDA'} (
                    {hardware.gpu_devices[0]?.free_memory_mb} MB VRAM)
                  </span>
                </>
              ) : (
                <>
                  <span className="w-2 h-2 rounded-full bg-slate-500" />
                  <span className="text-slate-400">Device: CPU Fallback (CUDA Unavailable)</span>
                </>
              )}
            </div>
            <div className="w-px h-3 bg-slate-800" />
            <div className="text-slate-400">PyTorch {hardware.pytorch_version}</div>
          </div>
        )}
      </div>

      {errorMsg && (
        <div className="mx-8 mt-4 p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg flex items-center gap-2 text-xs text-rose-300">
          <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Main Content */}
      <div className="p-8">
        {activeTab === 'jobs' ? (
          /* Recent Jobs Table */
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white">All Training Experiments</h2>
              <button
                onClick={async () => {
                  const j = await api.getTrainingJobs();
                  setJobs(j);
                }}
                className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
                title="Refresh jobs"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>

            {jobs.length === 0 ? (
              <div className="p-12 text-center text-slate-500 text-xs">
                No training runs have been executed yet. Click &quot;Start New Run&quot; to configure your first model training.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-slate-800 bg-slate-950/40 text-slate-400">
                      <th className="py-3 px-4 font-medium">Run Name</th>
                      <th className="py-3 px-4 font-medium">Task</th>
                      <th className="py-3 px-4 font-medium">Model</th>
                      <th className="py-3 px-4 font-medium">Status</th>
                      <th className="py-3 px-4 font-medium">Progress</th>
                      <th className="py-3 px-4 font-medium">Best Metric</th>
                      <th className="py-3 px-4 font-medium">Device</th>
                      <th className="py-3 px-4 font-medium">Created</th>
                      <th className="py-3 px-4 font-medium text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {jobs.map((job) => (
                      <tr key={job.id} className="hover:bg-slate-800/30 transition">
                        <td className="py-3 px-4 font-medium text-white">
                          <button
                            onClick={() => navigate(`/training/${job.id}`)}
                            className="hover:text-indigo-400 transition flex items-center gap-1.5 text-left"
                          >
                            <span>{job.name || job.id.slice(0, 8)}</span>
                            <ChevronRight className="w-3.5 h-3.5 opacity-50" />
                          </button>
                        </td>
                        <td className="py-3 px-4 text-slate-300">
                          <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 border border-slate-700">
                            {job.task_type || 'Image Classification'}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-300 font-mono text-[11px]">
                          {job.model_architecture || 'resnet18'}
                        </td>
                        <td className="py-3 px-4">{getStatusBadge(job.status)}</td>
                        <td className="py-3 px-4 text-slate-400">
                          Epoch {job.current_epoch} / {job.total_epochs}
                        </td>
                        <td className="py-3 px-4">
                          {job.best_metric_value !== null && job.best_metric_value !== undefined ? (
                            <span className="text-emerald-400 font-semibold">
                              {(job.best_metric_value * 100).toFixed(1)}% ({job.best_metric_name || 'score'})
                            </span>
                          ) : (
                            <span className="text-slate-500">—</span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-slate-400 uppercase font-mono text-[10px]">
                          {job.device || 'cpu'}
                        </td>
                        <td className="py-3 px-4 text-slate-400">
                          {new Date(job.created_at).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                            month: 'short',
                            day: 'numeric',
                          })}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => navigate(`/training/${job.id}`)}
                            className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs transition"
                          >
                            Monitor
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ) : (
          /* Training Wizard */
          <div className="space-y-6 max-w-5xl">
            {/* Step 1: Project & Dataset Selection */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
                <FolderKanban className="w-4 h-4 text-indigo-400" />
                <h2 className="text-sm font-semibold text-white">
                  1. Select Project & Dataset ({isDetection ? 'Object Detection' : 'Image Classification'})
                </h2>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">
                    Project
                  </label>
                  <select
                    value={selectedProjectId}
                    onChange={(e) => setSelectedProjectId(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    {projects.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} [{p.task_type}]
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">
                    Dataset
                  </label>
                  <select
                    value={selectedDatasetId}
                    onChange={(e) => setSelectedDatasetId(e.target.value)}
                    disabled={datasets.length === 0}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500 disabled:opacity-50"
                  >
                    {datasets.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name} ({d.image_count} images)
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Dataset Validation Card */}
              {validating ? (
                <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 flex items-center justify-center gap-2 text-xs text-slate-400">
                  <RefreshCw className="w-3.5 h-3.5 animate-spin text-indigo-400" />
                  Validating dataset annotations, {isDetection ? 'bounding boxes' : 'labels'}, and splits...
                </div>
              ) : validationResult ? (
                <div
                  className={`p-4 rounded-lg border text-xs space-y-3 ${
                    validationResult.is_valid
                      ? 'bg-emerald-950/20 border-emerald-500/30 text-emerald-200'
                      : 'bg-rose-950/20 border-rose-500/30 text-rose-200'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 font-semibold">
                      {validationResult.is_valid ? (
                        <>
                          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                          <span>Dataset Validation Passed</span>
                        </>
                      ) : (
                        <>
                          <ShieldAlert className="w-4 h-4 text-rose-400" />
                          <span>Dataset Validation Failed</span>
                        </>
                      )}
                    </div>
                    <div className="text-slate-400">
                      Split Preview: {validationResult.train_count} Train / {validationResult.val_count} Val / {validationResult.test_count} Test
                    </div>
                  </div>

                  {/* Summary Counters */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-[11px]">
                    <div className="p-2 rounded bg-slate-900/80 border border-slate-800">
                      <span className="text-slate-400 block">Valid Images</span>
                      <span className="text-white font-bold">{validationResult.valid_annotated_images}</span>
                    </div>
                    {isDetection && (
                      <div className="p-2 rounded bg-slate-900/80 border border-slate-800">
                        <span className="text-slate-400 block">Bounding Boxes</span>
                        <span className="text-white font-bold">{validationResult.total_bounding_boxes || 0}</span>
                      </div>
                    )}
                    <div className="p-2 rounded bg-slate-900/80 border border-slate-800">
                      <span className="text-slate-400 block">Negative Images</span>
                      <span className="text-white font-bold">{validationResult.negative_images}</span>
                    </div>
                    <div className="p-2 rounded bg-slate-900/80 border border-slate-800">
                      <span className="text-slate-400 block">Unannotated</span>
                      <span className="text-white font-bold">{validationResult.unannotated_images}</span>
                    </div>
                  </div>

                  {/* Class Distribution Badges */}
                  <div>
                    <div className="text-[11px] font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">
                      Classes ({validationResult.classes.length}):
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {validationResult.classes.map((cls) => (
                        <div
                          key={cls.label_id}
                          className="px-2.5 py-1 rounded bg-slate-900 border border-slate-800 flex items-center gap-2"
                        >
                          <span
                            className="w-2 h-2 rounded-full"
                            style={{ backgroundColor: cls.color }}
                          />
                          <span className="font-medium text-white">{cls.name}</span>
                          <span className="px-1.5 py-0.2 rounded bg-slate-800 text-[10px] text-slate-400 font-mono">
                            {cls.count} {isDetection ? 'boxes' : 'samples'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Warnings & Errors */}
                  {validationResult.errors.length > 0 && (
                    <div className="space-y-1 text-rose-300">
                      {validationResult.errors.map((e, idx) => (
                        <div key={idx} className="flex items-center gap-1.5">
                          <XCircle className="w-3.5 h-3.5 flex-shrink-0" />
                          <span>{e}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {validationResult.warnings.length > 0 && (
                    <div className="space-y-1 text-amber-300">
                      {validationResult.warnings.map((w, idx) => (
                        <div key={idx} className="flex items-center gap-1.5">
                          <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
                          <span>{w}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : null}
            </div>

            {/* Step 2: Model Architecture Selection */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
                <Boxes className="w-4 h-4 text-indigo-400" />
                <h2 className="text-sm font-semibold text-white">
                  2. Select Neural Network Architecture ({isDetection ? 'Detection Models' : 'Classification Models'})
                </h2>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {filteredModels.map((m) => {
                  const isSelected = selectedModelId === m.id;
                  return (
                    <div
                      key={m.id}
                      onClick={() => handleSelectModel(m)}
                      className={`p-4 rounded-xl border cursor-pointer transition flex flex-col justify-between ${
                        isSelected
                          ? 'bg-indigo-600/10 border-indigo-500 shadow-sm shadow-indigo-500/10'
                          : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div>
                        <div className="flex items-center justify-between mb-1.5">
                          <h3 className="text-xs font-bold text-white">{m.name}</h3>
                          <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] text-slate-400 font-mono">
                            {m.parameters_count_million}M Params
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-400 leading-relaxed line-clamp-2">
                          {m.description}
                        </p>
                      </div>

                      <div className="mt-3 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-500">
                        <span>Input: {m.default_input_size}px</span>
                        <span className="text-indigo-400 font-medium">
                          {m.pretrained_available ? 'Pretrained' : 'From Scratch'}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Step 3: Hyperparameters & Training Settings */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
                <Sliders className="w-4 h-4 text-indigo-400" />
                <h2 className="text-sm font-semibold text-white">3. Configure Hyperparameters & Hardware</h2>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Experiment Run Name
                  </label>
                  <input
                    type="text"
                    value={runName}
                    onChange={(e) => setRunName(e.target.value)}
                    placeholder={isDetection ? 'e.g. fasterrcnn_run1' : 'e.g. resnet18_baseline'}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Device
                  </label>
                  <select
                    value={hyperparams.device}
                    onChange={(e) => setHyperparams({ ...hyperparams, device: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="auto">Auto (CUDA if available)</option>
                    {hardware?.cuda_available && <option value="cuda">NVIDIA GPU (CUDA)</option>}
                    <option value="cpu">CPU Only</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Epochs
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={200}
                    value={hyperparams.epochs}
                    onChange={(e) => setHyperparams({ ...hyperparams, epochs: parseInt(e.target.value) || 10 })}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Batch Size
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={128}
                    value={hyperparams.batch_size}
                    onChange={(e) => setHyperparams({ ...hyperparams, batch_size: parseInt(e.target.value) || (isDetection ? 2 : 16) })}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Learning Rate
                  </label>
                  <input
                    type="number"
                    step={0.0001}
                    value={hyperparams.learning_rate}
                    onChange={(e) => setHyperparams({ ...hyperparams, learning_rate: parseFloat(e.target.value) || 0.001 })}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Optimizer
                  </label>
                  <select
                    value={hyperparams.optimizer}
                    onChange={(e) => setHyperparams({ ...hyperparams, optimizer: e.target.value as any })}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="SGD">SGD (with Momentum)</option>
                    <option value="AdamW">AdamW</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Image Input Resolution
                  </label>
                  <select
                    value={hyperparams.input_size}
                    onChange={(e) => setHyperparams({ ...hyperparams, input_size: parseInt(e.target.value) || (isDetection ? 800 : 224) })}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    {isDetection ? (
                      <>
                        <option value={320}>320 × 320 (Lightweight)</option>
                        <option value={600}>600 × 600</option>
                        <option value={800}>800 × 800 (Standard)</option>
                        <option value={1024}>1024 × 1024 (High-Res)</option>
                      </>
                    ) : (
                      <>
                        <option value={128}>128 × 128</option>
                        <option value={224}>224 × 224 (Standard)</option>
                        <option value={256}>256 × 256</option>
                      </>
                    )}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Pretrained Weights
                  </label>
                  <label className="flex items-center gap-2 mt-2 cursor-pointer text-xs text-slate-300">
                    <input
                      type="checkbox"
                      checked={hyperparams.pretrained}
                      onChange={(e) => setHyperparams({ ...hyperparams, pretrained: e.target.checked })}
                      className="rounded bg-slate-950 border-slate-700 text-indigo-600 focus:ring-0"
                    />
                    <span>Transfer Learning</span>
                  </label>
                </div>

                {isDetection && (
                  <>
                    <div>
                      <label className="block text-xs font-medium text-slate-300 mb-1">
                        Confidence Threshold
                      </label>
                      <input
                        type="number"
                        step={0.05}
                        min={0.05}
                        max={0.95}
                        value={hyperparams.confidence_threshold || 0.5}
                        onChange={(e) => setHyperparams({ ...hyperparams, confidence_threshold: parseFloat(e.target.value) || 0.5 })}
                        className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-slate-300 mb-1">
                        IoU Match Threshold
                      </label>
                      <input
                        type="number"
                        step={0.05}
                        min={0.1}
                        max={0.9}
                        value={hyperparams.iou_threshold || 0.5}
                        onChange={(e) => setHyperparams({ ...hyperparams, iou_threshold: parseFloat(e.target.value) || 0.5 })}
                        className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
                      />
                    </div>
                  </>
                )}
              </div>

              {/* Data Augmentation Toggles */}
              <div className="pt-3 border-t border-slate-800/80">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-2">
                  Data Augmentation
                </span>
                <div className="flex flex-wrap items-center gap-6 text-xs text-slate-300">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={hyperparams.horizontal_flip}
                      onChange={(e) => setHyperparams({ ...hyperparams, horizontal_flip: e.target.checked })}
                      className="rounded bg-slate-950 border-slate-700 text-indigo-600 focus:ring-0"
                    />
                    <span>Random Horizontal Flip (Synchronized Boxes)</span>
                  </label>
                </div>
              </div>
            </div>

            {/* Launch Button Action */}
            <div className="flex items-center justify-between pt-2">
              <div className="text-xs text-slate-400">
                {!validationResult?.is_valid && (
                  <span className="text-amber-400">
                    * Fix dataset validation errors above before starting training.
                  </span>
                )}
              </div>

              <button
                onClick={handleStartTraining}
                disabled={!validationResult?.is_valid || startingJob}
                className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-500 disabled:cursor-not-allowed text-white font-semibold rounded-xl text-xs shadow-lg shadow-indigo-600/20 transition"
              >
                {startingJob ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Launching Worker Process...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-current" />
                    Start {isDetection ? 'Detection' : 'Classification'} Training Worker
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
