import { ArrowRight, Radar } from "lucide-react";
import { Button } from "@/components/Button";

export function SplashScreen({ onEnter }: { onEnter: () => void }) {
  return (
    <main className="relative grid min-h-screen place-items-center overflow-hidden px-6 py-10">
      <div className="absolute aspect-square w-[min(74vw,860px)] rounded-full border border-cyan/20 shadow-[inset_0_0_80px_rgba(85,245,255,0.05)]" />
      <div className="orbit orbit-a" />
      <div className="orbit orbit-b" />
      <div className="scanline" />
      <section className="relative z-10 w-[min(900px,92vw)] rounded-[34px] border border-white/15 bg-gradient-to-br from-[#0b101c]/80 to-[#0e1523]/55 p-8 shadow-panel backdrop-blur-2xl md:p-14">
        <p className="mb-4 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.22em] text-cyan">
          <Radar className="h-4 w-4" />
          ZhihuFlow Agent Console
        </p>
        <h1 className="max-w-4xl text-[clamp(44px,7vw,88px)] font-black leading-[0.94] tracking-[-0.06em] text-white">
          把卡文交给 Agent，
          <br />
          把判断留给自己。
        </h1>
        <p className="mt-7 max-w-2xl text-lg leading-8 text-slate-400">
          热点发现、Deep Research、知乎长文生成、质量评估、邮件投递和历史复盘，
          都收进一个本地控制台。
        </p>
        <Button className="mt-8" size="lg" onClick={onEnter}>
          进入控制台
          <ArrowRight className="h-5 w-5" />
        </Button>
      </section>
    </main>
  );
}
