export interface WebSettings {
  schedule_enabled: boolean;
  email_delivery_enabled: boolean;
  offline: boolean;
  daily_at: string;
  seeds: string[];
  min_chars: number;
  max_chars: number;
}

export interface CurrentJob {
  job_id?: string;
  status: "idle" | "running" | "completed" | "failed";
  reason?: "manual" | "schedule";
  trace_id?: string;
  started_at?: string;
  finished_at?: string;
  error?: string;
}

export interface WebStatus {
  app: "ZhihuFlow";
  now: string;
  settings: WebSettings;
  email_configured: boolean;
  current_job: CurrentJob;
  history_count: number;
}

export interface HistoryRecord {
  trace_id: string;
  title: string;
  topic: string;
  created_at: string;
  reason: "manual" | "schedule";
  article_path: string;
  summary_path: string;
  quality?: number;
  risk?: string;
  delivered: boolean;
  delivery_message?: string;
}
