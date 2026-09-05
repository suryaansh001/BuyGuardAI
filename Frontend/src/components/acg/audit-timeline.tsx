import { AnimatePresence, motion } from "motion/react";
import { ChevronRight, ScrollText } from "lucide-react";
import { useState } from "react";
import { cn, formatAuditEventTitle } from "@/lib/utils";
import { ActorBadge, GlassPanel, SectionLabel } from "./primitives";
import type { AuditLogEntry } from "@/lib/types";

function mapActorToTone(actor: string): "buyer" | "merchant" | "approved" | "blocked" | "neutral" {
  const lower = actor.toLowerCase();
  if (lower.includes("buyer")) return "buyer";
  if (lower.includes("merchant")) return "merchant";
  if (lower.includes("policy")) return "approved";
  if (lower.includes("human")) return "blocked";
  if (lower.includes("system")) return "neutral";
  return "neutral";
}

const toneRing: Record<string, string> = {
  buyer: "text-buyer",
  merchant: "text-merchant",
  approved: "text-approved",
  blocked: "text-blocked",
  neutral: "text-muted-foreground",
};

function EventCard({ event }: { event: AuditLogEntry }) {
  const [open, setOpen] = useState(false);
  const tone = toneRing[mapActorToTone(event.actor)];

  const formattedTime = new Date(event.created_at).toLocaleTimeString("en-IN", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  return (
    <motion.li
      layout
      initial={{ opacity: 0, x: -18 }}
      animate={{ opacity: 1, x: 0 }}
      className="relative pl-10"
    >
      <span
        className={cn(
          "absolute left-[13px] top-4 size-2.5 -translate-x-1/2 rounded-full bg-current",
          tone,
        )}
        style={{ boxShadow: "0 0 14px 1px currentColor" }}
      />
      <div className="rounded-xl border border-border bg-foreground/5 transition hover:border-foreground/20">
        <button
          onClick={() => setOpen((v) => !v)}
          className="flex w-full items-center gap-3 px-4 py-3 text-left"
        >
          <ActorBadge actor={event.actor as any} />
          <span className="flex-1 text-sm font-medium">{formatAuditEventTitle(event.event)}</span>
          <span className="font-mono text-[11px] text-muted-foreground">{formattedTime}</span>
          <ChevronRight
            className={cn("size-4 text-muted-foreground transition", open && "rotate-90")}
          />
        </button>
        <AnimatePresence initial={false}>
          {open ? (
            <motion.pre
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden border-t border-border px-4 font-mono text-[11px] leading-relaxed text-muted-foreground"
            >
              <code className="block py-3">{JSON.stringify(event.payload, null, 2)}</code>
            </motion.pre>
          ) : null}
        </AnimatePresence>
      </div>
    </motion.li>
  );
}

export function AuditTimeline({ events }: { events: AuditLogEntry[] }) {
  return (
    <GlassPanel className="p-5">
      <div className="flex items-center justify-between">
        <SectionLabel icon={<ScrollText className="size-3.5" />} tone="buyer">
          Transaction Audit Trail
        </SectionLabel>
        <span className="font-mono text-[11px] text-muted-foreground">
          {events.length} immutable events
        </span>
      </div>

      {events.length === 0 ? (
        <p className="mt-6 text-sm text-muted-foreground">
          No events yet — run the buyer agent to start recording the trail.
        </p>
      ) : (
        <ol className="relative mt-5 space-y-3">
          <span className="absolute bottom-2 left-[13px] top-2 w-px bg-gradient-to-b from-buyer/60 via-border to-transparent" />
          <AnimatePresence initial={false}>
            {events.map((e, i) => (
              <EventCard key={e.id} event={e} index={i} />
            ))}
          </AnimatePresence>
        </ol>
      )}
    </GlassPanel>
  );
}