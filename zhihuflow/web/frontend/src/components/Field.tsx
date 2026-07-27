import * as LabelPrimitive from "@radix-ui/react-label";
import type { InputHTMLAttributes, TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

const inputClass =
  "mt-2 w-full rounded-2xl border border-white/10 bg-black/25 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan/60 focus:ring-4 focus:ring-cyan/10";

interface InputFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
}

export function InputField({ className, label, ...props }: InputFieldProps) {
  return (
    <LabelPrimitive.Root className="block text-sm font-medium text-slate-400">
      {label}
      <input className={cn(inputClass, className)} {...props} />
    </LabelPrimitive.Root>
  );
}

interface TextareaFieldProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
}

export function TextareaField({ className, label, ...props }: TextareaFieldProps) {
  return (
    <LabelPrimitive.Root className="block text-sm font-medium text-slate-400">
      {label}
      <textarea className={cn(inputClass, "min-h-32 resize-y leading-7", className)} {...props} />
    </LabelPrimitive.Root>
  );
}
