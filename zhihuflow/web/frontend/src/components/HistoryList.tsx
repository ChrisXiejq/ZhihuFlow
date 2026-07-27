import { FileText, MailCheck, MailX } from "lucide-react";
import { Badge, Card } from "@/components/Card";
import { Button } from "@/components/Button";
import type { HistoryRecord } from "@/types";

interface HistoryListProps {
  history: HistoryRecord[];
  onOpenArticle: (record: HistoryRecord) => void;
}

export function HistoryList({ history, onOpenArticle }: HistoryListProps) {
  if (!history.length) {
    return (
      <Card className="border-dashed border-white/15 bg-white/[0.04] text-slate-400">
        还没有历史文章。可以先点一次“立即触发发文”。
      </Card>
    );
  }

  return (
    <div className="grid gap-4">
      {history.map((record) => (
        <article
          key={record.trace_id}
          className="grid gap-5 rounded-[22px] border border-white/10 bg-[#121a2b]/90 p-5 shadow-[0_18px_52px_rgba(0,0,0,0.24)] transition hover:-translate-y-0.5 hover:border-cyan/30 md:grid-cols-[1fr_auto]"
        >
          <div>
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <Badge>{record.reason === "schedule" ? "定时任务" : "手动触发"}</Badge>
              <Badge tone={record.delivered ? "ok" : "warn"}>
                {record.delivered ? <MailCheck className="mr-1 inline h-3 w-3" /> : <MailX className="mr-1 inline h-3 w-3" />}
                {record.delivered ? "已投递" : "本地生成"}
              </Badge>
            </div>
            <h4 className="text-lg font-extrabold text-white">{record.title || "未命名文章"}</h4>
            <p className="mt-2 text-sm text-slate-400">{record.topic || "未知主题"}</p>
            <p className="mt-2 text-xs text-slate-500">{record.created_at}</p>
          </div>
          <div className="flex flex-col justify-between gap-4 md:items-end">
            <div className="flex gap-2 text-sm text-slate-300">
              <span>质量 {formatScore(record.quality)}</span>
              <span>风险 {record.risk || "--"}</span>
            </div>
            <Button variant="ghost" onClick={() => onOpenArticle(record)}>
              <FileText className="h-4 w-4" />
              预览
            </Button>
          </div>
        </article>
      ))}
    </div>
  );
}

function formatScore(value?: number) {
  if (value === undefined || value === null) {
    return "--";
  }
  return Number(value).toFixed(2);
}
