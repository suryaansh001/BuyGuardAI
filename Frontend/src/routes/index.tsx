import { createFileRoute } from "@tanstack/react-router";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import { Activity, Bot, CircleUser, FlaskConical, ShieldCheck, Store, MessageSquare, Handshake } from "lucide-react";
import { cn } from "@/lib/utils";
import { CONSTRAINTS, inr } from "@/lib/acg-data";
import { BuyerStudio } from "@/components/acg/buyer-studio";
import { MerchantCenter } from "@/components/acg/merchant-center";
import { NegotiationCenter } from "@/components/acg/negotiation-center";
import { Chip, StatusDot } from "@/components/acg/primitives";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Agent Commerce Gateway — Agentic Commerce Control Room" },
      {
        name: "description",
        content:
          "Deterministic AI agent commerce: buyer agents negotiate, policy engine enforces spend limits, Razorpay settles. Built for Razorpay Buildathon 2026.",
      },
      { property: "og:title", content: "Agent Commerce Gateway — Agentic Commerce Control Room" },
      {
        property: "og:description",
        content:
          "Watch buyer and merchant agents negotiate under deterministic guardrails with a full transaction audit trail.",
      },
    ],
  }),
  component: Index,
});

const TABS = [
  { key: "buyer" as const, label: "Buyer Studio", icon: Bot, tone: "buyer" },
  { key: "merchant" as const, label: "Merchant Center", icon: Store, tone: "merchant" },
  { key: "negotiation" as const, label: "Negotiation", icon: Handshake, tone: "merchant" },
];

function Index() {
  const [tab, setTab] = useState<"buyer" | "merchant">("buyer");

  return (
    <div className="relative min-h-screen bg-background text-foreground">
      <div
        className="pointer-events-none fixed inset-0"
        style={{
          background:
            "radial-gradient(60rem 40rem at 10% -10%, color-mix(in oklab, var(--buyer) 12%, transparent), transparent), radial-gradient(50rem 36rem at 95% 0%, color-mix(in oklab, var(--merchant) 10%, transparent), transparent)",
        }}
      />

      <header className="sticky top-0 z-30 border-b border-border/60 bg-background/70 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center gap-4 px-5 py-4">
          <div className="flex items-center gap-3">
            <div className="grid size-10 place-items-center rounded-xl border border-buyer/30 bg-buyer/10 text-buyer">
              <Activity className="size-5" />
            </div>
            <div>
              <h1 className="text-sm font-semibold tracking-tight sm:text-base">
                Agent Commerce Gateway
              </h1>
              <p className="font-mono text-[11px] text-muted-foreground">
                acg/1.0 · deterministic agentic commerce
              </p>
            </div>
          </div>

          <div className="ml-auto flex flex-wrap items-center gap-2">
            <Chip tone="approved">
              <StatusDot tone="approved" /> SYSTEM HEALTHY
            </Chip>
            <Chip tone="buyer">
              <ShieldCheck className="size-3" /> Auto-approve {"<"} {inr(CONSTRAINTS.autoApproveUnder)}
            </Chip>
            <Chip tone="neutral">Daily cap {inr(CONSTRAINTS.dailyLimit)}</Chip>
            <div className="flex items-center gap-2 rounded-full border border-border bg-foreground/5 py-1 pl-1 pr-3">
              <span className="grid size-7 place-items-center rounded-full bg-foreground/10">
                <CircleUser className="size-4 text-muted-foreground" />
              </span>
              <span className="text-xs text-muted-foreground">ops@acg.dev</span>
            </div>
          </div>
        </div>

        <div className="mx-auto max-w-[1400px] px-5 pb-4">
          <div className="inline-flex rounded-2xl border border-border bg-foreground/5 p-1">
            {TABS.map((t) => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={cn(
                  "relative flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition",
                  tab === t.key
                    ? t.tone === "buyer"
                      ? "text-buyer"
                      : "text-merchant"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {tab === t.key ? (
                  <motion.span
                    layoutId="main-tab"
                    className={cn(
                      "absolute inset-0 rounded-xl border",
                      t.tone === "buyer"
                        ? "border-buyer/40 bg-buyer/10"
                        : "border-merchant/40 bg-merchant/10",
                    )}
                  />
                ) : null}
                <t.icon className="relative size-4" />
                <span className="relative">{t.label}</span>
              </button>
            ))}
          </div>
        </div>
      </header>

      <main className="relative mx-auto max-w-[1400px] px-5 py-6 pb-28">
        <AnimatePresence mode="wait">
          <motion.div
            key={tab}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
          >
            {tab === "buyer" ? (
              <BuyerStudio />
            ) : tab === "merchant" ? (
              <MerchantCenter />
            ) : (
              <NegotiationCenter />
            )}
          </motion.div>
        </AnimatePresence>
      </main>

      <DevToolbar onBuyerTab={() => setTab("buyer")} />
    </div>
  );
}

function DevToolbar({
  onBuyerTab,
}: {
  onBuyerTab: () => void;
}) {
  const [open, setOpen] = useState(true);

  return (
    <div className="fixed bottom-5 right-5 z-40">
      <AnimatePresence>
        {open ? (
          <motion.div
            initial={{ opacity: 0, y: 12, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.97 }}
            className="glass mb-3 w-72 rounded-2xl p-4"
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                Dev Toolbar
              </span>
              <StatusDot tone="buyer" />
            </div>
            <div className="mt-3 space-y-2">
              <button
                onClick={() => {
                  onBuyerTab();
                  const input = document.querySelector('input[placeholder*="mechanical keyboard"]') as HTMLInputElement;
                  if (input) {
                    input.value = "usb hub under ₹2000";
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                  }
                }}
                className="w-full rounded-xl border border-border bg-foreground/5 px-3 py-2.5 text-left text-xs transition hover:text-foreground"
              >
                <span className="block font-medium">Auto-Approve Flow</span>
                <span className="mt-0.5 block font-mono text-[10px] opacity-80">
                  usb hub under ₹2000 (guaranteed under ₹3,000 threshold)
                </span>
              </button>
              <button
                onClick={() => {
                  onBuyerTab();
                  const input = document.querySelector('input[placeholder*="mechanical keyboard"]') as HTMLInputElement;
                  if (input) {
                    input.value = "mechanical keyboard under ₹5000";
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                  }
                }}
                className="w-full rounded-xl border border-border bg-foreground/5 px-3 py-2.5 text-left text-xs transition hover:text-foreground"
              >
                <span className="block font-medium">Over Threshold Flow</span>
                <span className="mt-0.5 block font-mono text-[10px] opacity-80">
                  mechanical keyboard under ₹5000 (triggers approval)
                </span>
              </button>
              <button
                onClick={() => {
                  onBuyerTab();
                  const input = document.querySelector('input[placeholder*="mechanical keyboard"]') as HTMLInputElement;
                  if (input) {
                    input.value = "4k monitor under ₹40000";
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                  }
                }}
                className="w-full rounded-xl border border-border bg-foreground/5 px-3 py-2.5 text-left text-xs transition hover:text-foreground"
              >
                <span className="block font-medium">Blocked Flow</span>
                <span className="mt-0.5 block font-mono text-[10px] opacity-80">
                  4k monitor under ₹40000 (exceeds max transaction)
                </span>
              </button>
              <button
                onClick={() => {
                  onBuyerTab();
                  const input = document.querySelector('input[placeholder*="mechanical keyboard"]') as HTMLInputElement;
                  if (input) {
                    input.value = "mechanical keyboard under ₹5000";
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                  }
                  alert("For payment failure test: Complete the approval flow, then use failure@razorpay as UPI ID during checkout");
                }}
                className="w-full rounded-xl border border-blocked/40 bg-blocked/5 px-3 py-2.5 text-left text-xs text-blocked transition hover:bg-blocked/10"
              >
                <span className="block font-medium">Payment Failure Test</span>
                <span className="mt-0.5 block font-mono text-[10px] opacity-80">
                  Use failure@razorpay UPI ID in checkout
                </span>
              </button>
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>

      <button
        onClick={() => setOpen((v) => !v)}
        className="ml-auto flex items-center gap-2 rounded-full border border-buyer/40 bg-buyer/10 px-4 py-2.5 text-xs font-medium text-buyer backdrop-blur-xl transition hover:bg-buyer/20"
      >
        <FlaskConical className="size-4" />
        Dev Toolbar
      </button>
    </div>
  );
}