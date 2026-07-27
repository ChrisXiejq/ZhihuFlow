import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { Button } from "@/components/Button";

interface ArticlePreviewDialogProps {
  preview: { title: string; body: string } | null;
  onClose: () => void;
}

export function ArticlePreviewDialog({ onClose, preview }: ArticlePreviewDialogProps) {
  return (
    <Dialog.Root open={Boolean(preview)} onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/65 backdrop-blur-md" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 h-[min(760px,88vh)] w-[min(1040px,92vw)] -translate-x-1/2 -translate-y-1/2 rounded-3xl border border-white/10 bg-[#09101d] p-5 text-white shadow-panel focus:outline-none">
          <div className="mb-4 flex items-center justify-between gap-4">
            <Dialog.Title className="text-lg font-extrabold">{preview?.title ?? "文章预览"}</Dialog.Title>
            <Dialog.Close asChild>
              <Button variant="ghost">
                <X className="h-4 w-4" />
                关闭
              </Button>
            </Dialog.Close>
          </div>
          <pre className="h-[calc(100%-58px)] overflow-auto whitespace-pre-wrap rounded-2xl border border-white/10 bg-black/20 p-5 font-mono text-sm leading-7 text-slate-200">
            {preview?.body ?? ""}
          </pre>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
