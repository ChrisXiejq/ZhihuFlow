import { useEffect, useMemo, useState } from "react";
import { api } from "@/api";
import { ArticlePreviewDialog } from "@/components/ArticlePreviewDialog";
import { ConsoleShell } from "@/components/ConsoleShell";
import { SplashScreen } from "@/components/SplashScreen";
import type { CurrentJob, HistoryRecord, WebSettings, WebStatus } from "@/types";

export default function App() {
  const [entered, setEntered] = useState(false);
  const [settings, setSettings] = useState<WebSettings | null>(null);
  const [status, setStatus] = useState<WebStatus | null>(null);
  const [history, setHistory] = useState<HistoryRecord[]>([]);
  const [logs, setLogs] = useState<string[]>(["ZhihuFlow runtime online", "等待下一次内容任务"]);
  const [preview, setPreview] = useState<{ title: string; body: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const currentJob = status?.current_job ?? { status: "idle" as const };
  const isRunning = currentJob.status === "running";

  const appendLog = (message: string) => {
    setLogs((items) => [...items.slice(-7), message]);
  };

  const refresh = async () => {
    const [nextStatus, nextHistory] = await Promise.all([api.status(), api.history()]);
    setStatus(nextStatus);
    setHistory(nextHistory);
    if (nextStatus.current_job.status === "failed" && nextStatus.current_job.error) {
      appendLog(`任务失败：${nextStatus.current_job.error}`);
    }
  };

  const loadInitial = async () => {
    const [nextSettings, nextStatus, nextHistory] = await Promise.all([
      api.settings(),
      api.status(),
      api.history(),
    ]);
    setSettings(nextSettings);
    setStatus(nextStatus);
    setHistory(nextHistory);
  };

  const saveSettings = async (nextSettings: WebSettings) => {
    setBusy(true);
    try {
      const saved = await api.saveSettings(nextSettings);
      setSettings(saved);
      appendLog("配置已保存");
      await refresh();
    } catch (error) {
      appendLog(`配置保存失败：${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setBusy(false);
    }
  };

  const runNow = async (nextSettings: WebSettings) => {
    setBusy(true);
    try {
      const saved = await api.saveSettings(nextSettings);
      setSettings(saved);
      const job: CurrentJob = await api.run();
      appendLog(`发文任务已触发：${job.job_id ?? "running"}`);
      await refresh();
    } catch (error) {
      appendLog(`触发失败：${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setBusy(false);
    }
  };

  const openArticle = async (record: HistoryRecord) => {
    setPreview({ title: record.title, body: "加载文章中..." });
    try {
      const body = await api.article(record.trace_id);
      setPreview({ title: record.title, body });
    } catch (error) {
      setPreview({
        title: record.title,
        body: `读取失败：${error instanceof Error ? error.message : String(error)}`,
      });
    }
  };

  useEffect(() => {
    void loadInitial();
  }, []);

  useEffect(() => {
    if (!isRunning) {
      return;
    }
    const timer = window.setInterval(() => {
      void refresh();
    }, 2500);
    return () => window.clearInterval(timer);
  }, [isRunning]);

  const runtimeLabel = useMemo(() => {
    if (currentJob.status === "running") {
      return `Agent 运行中 · ${currentJob.reason ?? "manual"}`;
    }
    if (currentJob.status === "failed") {
      return "任务失败";
    }
    return "Agent 待命";
  }, [currentJob]);

  if (!entered) {
    return <SplashScreen onEnter={() => setEntered(true)} />;
  }

  return (
    <>
      <ConsoleShell
        busy={busy}
        history={history}
        logs={logs}
        runtimeLabel={runtimeLabel}
        settings={settings}
        status={status}
        onOpenArticle={openArticle}
        onRefresh={() => {
          appendLog("刷新运行状态");
          void refresh();
        }}
        onRunNow={runNow}
        onSaveSettings={saveSettings}
      />
      <ArticlePreviewDialog preview={preview} onClose={() => setPreview(null)} />
    </>
  );
}
