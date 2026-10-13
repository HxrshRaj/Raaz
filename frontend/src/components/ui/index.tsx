import * as DialogPrimitive from "@radix-ui/react-dialog";
import { Slot } from "@radix-ui/react-slot";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { cva, type VariantProps } from "class-variance-authority";
import { AlertTriangle, Loader2, X } from "lucide-react";
import { forwardRef, type ButtonHTMLAttributes, type HTMLAttributes, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

// ------------------------------------------------------------------ Button
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-45 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-glow",
  {
    variants: {
      variant: {
        brass: "bg-brass text-ink-900 hover:bg-brass-light shadow-[0_0_0_1px_rgba(0,0,0,.4)]",
        ghost: "text-paper-dim hover:bg-ink-600 hover:text-paper",
        outline: "border border-ink-500 bg-ink-800/60 text-paper hover:border-brass hover:text-brass-light",
        danger: "bg-blood text-white hover:bg-blood-light",
        quiet: "text-brass-light hover:text-amber-glow underline-offset-4 hover:underline",
      },
      size: { sm: "h-8 px-3", md: "h-10 px-4", lg: "h-12 px-6 text-base", icon: "h-9 w-9" },
    },
    defaultVariants: { variant: "outline", size: "md" },
  },
);
export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> { asChild?: boolean; loading?: boolean }
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, size, asChild, loading, children, disabled, ...props }, ref) => {
  const Comp = asChild ? Slot : "button";
  return (
    <Comp ref={ref} className={cn(buttonVariants({ variant, size }), className)} disabled={disabled || loading} {...props}>
      {asChild ? children : <>{loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}{children}</>}
    </Comp>
  );
});
Button.displayName = "Button";

// ------------------------------------------------------------------ Badge
const badgeVariants = cva("inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium", {
  variants: {
    tone: {
      neutral: "border-ink-500 bg-ink-800 text-paper-dim",
      brass: "border-brass-dark bg-brass/10 text-brass-light",
      red: "border-blood/60 bg-blood/15 text-blood-light",
      green: "border-emerald-700/60 bg-emerald-700/15 text-emerald-300",
      blue: "border-rain/50 bg-rain/10 text-sky-200",
      amber: "border-amber-deep/60 bg-amber-glow/10 text-amber-glow",
    },
  },
  defaultVariants: { tone: "neutral" },
});
export function Badge({ className, tone, ...props }: HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}

// ------------------------------------------------------------------ Form controls
const field = "w-full rounded-md border border-ink-500 bg-ink-800/80 px-3 text-sm text-paper placeholder:text-paper-mute focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-glow disabled:opacity-50";
export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(({ className, ...p }, ref) => (
  <input ref={ref} className={cn(field, "h-10", className)} {...p} />
));
Input.displayName = "Input";
export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(({ className, ...p }, ref) => (
  <textarea ref={ref} className={cn(field, "min-h-[44px] py-2.5", className)} {...p} />
));
Textarea.displayName = "Textarea";
export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(({ className, ...p }, ref) => (
  <select ref={ref} className={cn(field, "h-10 pr-8", className)} {...p} />
));
Select.displayName = "Select";

export function Progress({ value, className, tone = "brass" }: { value: number; className?: string; tone?: "brass" | "red" | "green" }) {
  const v = Math.max(0, Math.min(100, value));
  const color = tone === "red" ? "bg-blood" : tone === "green" ? "bg-emerald-500" : "bg-brass";
  return (
    <div role="progressbar" aria-valuenow={Math.round(v)} aria-valuemin={0} aria-valuemax={100} className={cn("h-2 w-full overflow-hidden rounded-full bg-ink-800", className)}>
      <div className={cn("h-full rounded-full transition-all duration-500", color)} style={{ width: `${v}%` }} />
    </div>
  );
}

// ------------------------------------------------------------------ Dialog
export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export function DialogContent({ title, description, children, className }: { title: string; description?: string; children: ReactNode; className?: string }) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm" />
      <DialogPrimitive.Content className={cn("fixed left-1/2 top-1/2 z-50 max-h-[88vh] w-[min(92vw,640px)] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-xl border border-ink-500 bg-ink-700 p-6 shadow-card", className)}>
        <DialogPrimitive.Title className="font-display text-2xl text-brass-light">{title}</DialogPrimitive.Title>
        <DialogPrimitive.Description className={description ? "mt-1 text-sm text-paper-mute" : "sr-only"}>{description ?? title}</DialogPrimitive.Description>
        <div className="mt-4">{children}</div>
        <DialogPrimitive.Close className="absolute right-3 top-3 rounded p-1 text-paper-mute hover:text-paper" aria-label="Close"><X className="h-4 w-4" /></DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

// ------------------------------------------------------------------ Tabs
export const Tabs = TabsPrimitive.Root;
export const TabsList = ({ className, ...p }: TabsPrimitive.TabsListProps) => (
  <TabsPrimitive.List className={cn("inline-flex gap-1 rounded-lg border border-ink-500 bg-ink-800 p-1", className)} {...p} />
);
export const TabsTrigger = ({ className, ...p }: TabsPrimitive.TabsTriggerProps) => (
  <TabsPrimitive.Trigger className={cn("rounded-md px-3 py-1.5 text-sm text-paper-mute transition-colors data-[state=active]:bg-ink-500 data-[state=active]:text-paper hover:text-paper", className)} {...p} />
);
export const TabsContent = TabsPrimitive.Content;

// ------------------------------------------------------------------ Tooltip
export const TooltipProvider = TooltipPrimitive.Provider;
export function Tip({ label, children }: { label: string; children: ReactNode }) {
  return (
    <TooltipPrimitive.Root delayDuration={200}>
      <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content sideOffset={6} className="z-50 max-w-xs rounded-md border border-ink-500 bg-ink-900 px-2.5 py-1.5 text-xs text-paper shadow-card">{label}</TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  );
}

// ------------------------------------------------------------------ states
export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="flex items-center gap-2 text-paper-mute">
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> <span className="text-sm">{label}…</span>
    </div>
  );
}
export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cn("animate-pulse rounded-md bg-ink-600/60", className)} />;
}
export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const msg = error instanceof Error ? error.message : "Something went wrong.";
  return (
    <div role="alert" className="flex flex-col items-start gap-3 rounded-lg border border-blood/50 bg-blood/10 p-4 text-sm">
      <div className="flex items-center gap-2 text-blood-light"><AlertTriangle className="h-4 w-4" aria-hidden /> {msg}</div>
      {onRetry && <Button size="sm" onClick={onRetry}>Try again</Button>}
    </div>
  );
}
export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-ink-500 p-6 text-center">
      <p className="font-display text-lg text-paper-dim">{title}</p>
      {children && <p className="mt-1 text-sm text-paper-mute">{children}</p>}
    </div>
  );
}
