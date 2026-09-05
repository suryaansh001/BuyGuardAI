import { motion } from "motion/react";
import type { ReactNode } from "react";
import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import type { AuditActor } from "@/lib/acg-data";

type Tone = "buyer" | "merchant" | "approved" | "blocked" | "neutral";

const toneText: Record<Tone, string> = {
  buyer: "text-buyer",
  merchant: "text-merchant",
  approved: "text-approved",
  blocked: "text-blocked",
  neutral: "text-muted-foreground",
};

const toneBg: Record<Tone, string> = {
  buyer: "bg-buyer/10 border-buyer/30",
  merchant: "bg-merchant/10 border-merchant/30",
  approved: "bg-approved/10 border-approved/30",
  blocked: "bg-blocked/10 border-blocked/30",
  neutral: "bg-foreground/5 border-border",
};

export function GlassPanel({
  className,
  children,
  ...rest
}: { className?: string; children: ReactNode } & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("glass rounded-2xl", className)} {...rest}>
      {children}
    </div>
  );
}

export function SectionLabel({
  icon,
  children,
  tone = "neutral",
}: {
  icon?: ReactNode;
  children: ReactNode;
  tone?: Tone;
}) {
  return (
    <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
      {icon ? <span className={toneText[tone]}>{icon}</span> : null}
      {children}
    </div>
  );
}

export function Chip({
  children,
  tone = "neutral",
  className,
}: {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[11px] leading-none",
        toneBg[tone],
        toneText[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function StatusDot({ tone = "approved", pulse = true }: { tone?: Tone; pulse?: boolean }) {
  return (
    <span
      className={cn(
        "inline-block size-2 rounded-full bg-current",
        toneText[tone],
        pulse && "pulse-ring",
      )}
    />
  );
}

const actorTone: Record<string, Tone> = {
  SYSTEM: "neutral",
  "BUYER AGENT": "buyer",
  "MERCHANT AGENT": "merchant",
  "POLICY ENGINE": "approved",
  HUMAN: "blocked",
  SYSTEM: "neutral",
  BUYER_AGENT: "buyer",
  MERCHANT_AGENT: "merchant",
  POLICY_ENGINE: "approved",
  HUMAN: "blocked",
};

export function ActorBadge({ actor }: { actor: string }) {
  const normalized = actor.toUpperCase().replace(/\s+/g, "_");
  return (
    <Chip tone={actorTone[normalized] ?? "neutral"} className="uppercase tracking-wider">
      [{actor.toUpperCase()}]
    </Chip>
  );
}

export function AnimatedCounter({
  value,
  prefix = "",
  suffix = "",
  className,
}: {
  value: number;
  prefix?: string;
  suffix?: string;
  className?: string;
}) {
  const [display, setDisplay] = useState(0);
  const raf = useRef<number | null>(null);

  useEffect(() => {
    const start = performance.now();
    const duration = 1200;
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setDisplay(Math.round(value * eased));
      if (p < 1) raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
    };
  }, [value]);

  return (
    <span className={cn("font-mono tabular-nums", className)}>
      {prefix}
      {display.toLocaleString("en-IN")}
      {suffix}
    </span>
  );
}

export function FadeIn({
  children,
  delay = 0,
  className,
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay, ease: [0.22, 1, 0.36, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
