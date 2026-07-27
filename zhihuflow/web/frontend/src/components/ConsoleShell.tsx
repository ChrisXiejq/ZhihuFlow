import * as SwitchPrimitive from "@radix-ui/react-switch";
import { Clock3, History, Mail, Play, RefreshCw, Save, Settings, Sparkles } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Badge, Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { InputField, TextareaField } from "@/components/Field";
import { HistoryList } from "@/components/HistoryList";
import type { HistoryRecord, WebSettings, WebStatus } from "@/types";
import { cn } from "@/lib/utils";

const defaultSettings: WebSettings = {
  schedule_enabled: false,
  email_delivery_enabled: false,
  offline: false,
  daily_at: "09:00",
  seeds: ["LLM agent", "context engineering", "AI coding agent", "Agentic RAG"],
  min_chars: 1500,
  max_chars: 2500,
};

interface ConsoleShellProps {
  busy: boolean;
  history: HistoryRecord[];
  logs: string[];
  runtimeLabel: string;
  settings: WebSettings | null;
  status: WebStatus | null;
  onOpenArticle: (record: HistoryRecord) => void;
  onRefresh: () => void;
  onRunNow: (settings: WebSettings) => void;
  onSaveSettings: (settings: WebSettings) => void;
}

export function ConsoleShell({
  busy,
  history,
  logs,
  runtimeLabel,
  settings,
  status,
  onOpenArticle,
  onRefresh,
  onRunNow,
  onSaveSettings,
}: ConsoleShellProps) {
  const [draft, setDraft] = useState<WebSettings>(settings ?? defaultSettings);

  useEffect(() => {
    if (settings) {
      setDraft(settings);
    }
  }, [settings]);

  const updateDraft = (patch: Partial<WebSettings>) => {
    setDraft((current) => ({ ...current, ...patch }));
  };

  const jobStatus = status?.current_job.status ?? "idle";
  const emailConfigured = Boolean(status?.email_configured);

  return (
    <main className="grid min-h-screen grid-cols-1 lg:grid-cols-[280px_1fr]">
      <aside className="relative border-r border-white/10 bg-black/35 p-7 backdrop-blur-xl lg:sticky lg:top-0 lg:h-screen">
        <div className="mb-10 flex items-center gap-3">
          <span className="grid h-11 w-11 place-items-center rounded-2xl bg-cyan text-lg font-black text-[#061014]">知</span>
          <div>
            <strong className="text-white">ZhihuFlow</strong>
            <small className="block text-xs text-slate-400">Content Agent Harness</small>
          </div>
        </div>
        <nav className="grid gap-3">
          <NavItem href="#control" icon={<Settings className="h-4 w-4" />} label="控制台" />
          <NavItem href="#topics" icon={<Sparkles className="h-4 w-4" />} label="主题领域" />
          <NavItem href="#history" icon={<History className="h-4 w-4" />} label="历史文章" />
        </nav>
        <div className="mt-8 flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-400 lg:absolute lg:bottom-7 lg:left-7 lg:right-7">
          <span className={cn("h-2.5 w-2.5 rounded-full shadow-[0_0_18px_currentColor]", statusColor(jobStatus))} />
          {runtimeLabel}
        </div>
      </aside>

      <section className="p-5 md:p-8">
        <header className="mb-5 flex min-h-[310px] flex-col justify-end gap-6 rounded-[32px] border border-white/10 bg-[linear-gradient(135deg,rgba(85,245,255,.12),transparent_46%),linear-gradient(315deg,rgba(248,210,106,.1),transparent_46%),rgba(10,15,26,.62)] p-8 shadow-panel md:flex-row md:items-end md:justify-between">
          <div>
            <p className="mb-4 text-xs font-bold uppercase tracking-[0.22em] text-cyan">Daily Zhihu Draft Factory</p>
            <h1 className="max-w-3xl text-[clamp(30px,4vw,54px)] font-black leading-[1.02] tracking-[-0.04em] text-white">
              每天自动研究热点，生成一篇可审核草稿。
            </h1>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button disabled={busy || jobStatus === "running"} onClick={() => onRunNow(normalizeDraft(draft))}>
              <Play className="h-4 w-4" />
              立即触发发文
            </Button>
            <Button variant="ghost" onClick={onRefresh}>
              <RefreshCw className="h-4 w-4" />
              刷新状态
            </Button>
          </div>
        </header>

        <section id="control" className="grid grid-cols-12 gap-5">
          <Card
            className="col-span-12 xl:col-span-7"
            title="发文控制"
            action={<Badge tone={emailConfigured ? "ok" : "warn"}>{emailConfigured ? "邮箱已配置" : "邮箱未配置"}</Badge>}
          >
            <SwitchRow
              checked={draft.schedule_enabled}
              description="Web 服务运行时，到点自动生成文章。"
              icon={<Clock3 className="h-5 w-5" />}
              title="开启每日发文任务"
              onCheckedChange={(checked) => updateDraft({ schedule_enabled: checked })}
            />
            <SwitchRow
              checked={draft.email_delivery_enabled}
              description="关闭时只生成本地历史，不真实发邮件。"
              icon={<Mail className="h-5 w-5" />}
              title="生成后发送到邮箱"
              onCheckedChange={(checked) => updateDraft({ email_delivery_enabled: checked })}
            />
            <div className="my-5 grid gap-3 md:grid-cols-3">
              <InputField label="定时时间" type="time" value={draft.daily_at} onChange={(event) => updateDraft({ daily_at: event.target.value })} />
              <InputField
                label="最小字数"
                min={800}
                type="number"
                value={draft.min_chars}
                onChange={(event) => updateDraft({ min_chars: Number(event.target.value) })}
              />
              <InputField
                label="最大字数"
                min={1200}
                type="number"
                value={draft.max_chars}
                onChange={(event) => updateDraft({ max_chars: Number(event.target.value) })}
              />
            </div>
            <label className="mb-5 flex items-center gap-3 text-sm text-slate-400">
              <input
                checked={draft.offline}
                className="h-4 w-4 accent-cyan"
                type="checkbox"
                onChange={(event) => updateDraft({ offline: event.target.checked })}
              />
              离线演示模式
            </label>
            <Button disabled={busy} variant="secondary" onClick={() => onSaveSettings(normalizeDraft(draft))}>
              <Save className="h-4 w-4" />
              保存设置
            </Button>
          </Card>

          <Card className="col-span-12 xl:col-span-5" title="运行状态">
            <dl className="grid gap-3">
              <Stat label="当前任务" value={jobStatus} />
              <Stat label="历史文章" value={String(status?.history_count ?? 0)} />
              <Stat label="当前时间" value={status?.now ?? "--"} />
            </dl>
            <div className="mt-5 min-h-32 rounded-2xl border border-cyan/20 bg-[#020c12]/75 p-4 font-mono text-xs text-cyan">
              {logs.map((item, index) => (
                <p key={`${item}-${index}`} className="mb-2">
                  &gt; {item}
                </p>
              ))}
            </div>
          </Card>

          <Card
            id="topics"
            className="col-span-12"
            title="搜索主题领域"
            action={<Badge>最多 12 个种子词</Badge>}
          >
            <TextareaField
              label="主题种子词"
              placeholder="每行一个主题，例如：AI coding agent"
              value={draft.seeds.join("\n")}
              onChange={(event) => updateDraft({ seeds: event.target.value.split(/\n|,/).map((item) => item.trim()).filter(Boolean) })}
            />
            <p className="mt-3 text-sm text-slate-400">
              建议混合技术词、产品词和商业词：Agent memory、context engineering、AI 编程助手、知识库 RAG。
            </p>
          </Card>
        </section>

        <section id="history" className="mt-7">
          <div className="mb-4 flex flex-wrap items-end justify-between gap-4">
            <div>
              <h2 className="text-2xl font-black text-white">历史发文</h2>
              <p className="mt-2 text-sm text-slate-400">每次生成都会留下文章、质量分、风险等级和投递结果。</p>
            </div>
            <Badge>{history.length} 篇文章</Badge>
          </div>
          <HistoryList history={history} onOpenArticle={onOpenArticle} />
        </section>
      </section>
    </main>
  );
}

function NavItem({ href, icon, label }: { href: string; icon: ReactNode; label: string }) {
  return (
    <a className="flex items-center gap-3 rounded-2xl border border-transparent px-4 py-3 text-sm text-white transition hover:border-white/10 hover:bg-white/5" href={href}>
      {icon}
      {label}
    </a>
  );
}

function SwitchRow({
  checked,
  description,
  icon,
  title,
  onCheckedChange,
}: {
  checked: boolean;
  description: string;
  icon: ReactNode;
  title: string;
  onCheckedChange: (checked: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-5 border-t border-white/10 py-4">
      <div className="flex gap-3">
        <span className="mt-1 text-cyan">{icon}</span>
        <div>
          <strong className="text-white">{title}</strong>
          <p className="mt-1 text-sm text-slate-400">{description}</p>
        </div>
      </div>
      <SwitchPrimitive.Root
        checked={checked}
        className="relative h-8 w-[58px] shrink-0 rounded-full border border-white/10 bg-white/10 transition data-[state=checked]:border-cyan/40 data-[state=checked]:bg-cyan/20"
        onCheckedChange={onCheckedChange}
      >
        <SwitchPrimitive.Thumb className="block h-6 w-6 translate-x-1 rounded-full bg-slate-400 transition data-[state=checked]:translate-x-[29px] data-[state=checked]:bg-cyan data-[state=checked]:shadow-[0_0_18px_#55f5ff]" />
      </SwitchPrimitive.Root>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between border-b border-white/10 py-3 text-sm">
      <dt className="text-slate-400">{label}</dt>
      <dd className="font-extrabold text-white">{value}</dd>
    </div>
  );
}

function normalizeDraft(settings: WebSettings): WebSettings {
  const minChars = Math.max(800, Number(settings.min_chars || 1500));
  const maxChars = Math.max(minChars, Number(settings.max_chars || 2500));
  const seeds = settings.seeds.map((item) => item.trim()).filter(Boolean).slice(0, 12);
  return {
    ...settings,
    daily_at: settings.daily_at || "09:00",
    min_chars: minChars,
    max_chars: maxChars,
    seeds: seeds.length ? seeds : defaultSettings.seeds,
  };
}

function statusColor(status: string) {
  if (status === "running") {
    return "bg-gold text-gold";
  }
  if (status === "failed") {
    return "bg-danger text-danger";
  }
  return "bg-success text-success";
}
