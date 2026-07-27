import type { CurrentJob, HistoryRecord, WebSettings, WebStatus } from "@/types";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers ?? {}) },
    ...options,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = await response.json();
      detail = payload.error ?? detail;
    } catch {
      // Keep the HTTP status text.
    }
    throw new Error(detail);
  }
  const contentType = response.headers.get("Content-Type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json() as Promise<T>;
  }
  return response.text() as Promise<T>;
}

export const api = {
  status: () => request<WebStatus>("/api/status"),
  settings: () => request<WebSettings>("/api/settings"),
  saveSettings: (settings: WebSettings) =>
    request<WebSettings>("/api/settings", {
      method: "POST",
      body: JSON.stringify(settings),
    }),
  run: () =>
    request<CurrentJob>("/api/run", {
      method: "POST",
      body: "{}",
    }),
  history: () => request<HistoryRecord[]>("/api/history"),
  article: (traceId: string) => request<string>(`/api/articles/${encodeURIComponent(traceId)}`),
};
