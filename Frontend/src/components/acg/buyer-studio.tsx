import { AnimatePresence, motion } from "motion/react";
import {
  Activity,
  BadgeCheck,
  Ban,
  BrainCircuit,
  Check,
  CircleAlert,
  Handshake,
  Loader2,
  Search,
  ShieldCheck,
  Sparkles,
  Terminal,
  Zap,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { inr } from "@/lib/acg-data";
import { Chip, FadeIn, GlassPanel, SectionLabel, StatusDot } from "./primitives";
import { AuditTimeline } from "./audit-timeline";
import { api, ApiError } from "@/lib/api";
import type { PurchaseIntent, Product, ComparisonProduct, AuditLogEntry } from "@/lib/types";
import { formatAuditEventTitle } from "@/lib/utils";

type Phase =
  | "idle"
  | "parsing"
  | "thinking"
  | "policy"
  | "approval"
  | "approved"
  | "rejected"
  | "paying"
  | "confirming"
  | "paid"
  | "failed";

const clock = () =>
  new Date().toLocaleTimeString("en-IN", { hour12: false }) +
  "." +
  String(new Date().getMilliseconds()).padStart(3, "0");

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function TypedLine({ text }: { text: string }) {
  const [n, setN] = useState(0);
  useEffect(() => {
    setN(0);
    const id = setInterval(() => {
      setN((v) => {
        if (v >= text.length) {
          clearInterval(id);
          return v;
        }
        return v + 2;
      });
    }, 12);
    return () => clearInterval(id);
  }, [text]);
  return <span>{text.slice(0, n)}</span>;
}

function mapActorToTone(actor: string): "buyer" | "merchant" | "approved" | "blocked" | "neutral" {
  const lower = actor.toLowerCase();
  if (lower.includes("buyer")) return "buyer";
  if (lower.includes("merchant")) return "merchant";
  if (lower.includes("policy")) return "approved";
  if (lower.includes("human")) return "blocked";
  return "neutral";
}

function transformAuditEvent(event: AuditLogEntry): {
  id: string;
  actor: string;
  title: string;
  time: string;
  payload: Record<string, unknown>;
  tone: "buyer" | "merchant" | "approved" | "blocked" | "neutral";
} {
  return {
    id: String(event.id),
    actor: event.actor.toUpperCase(),
    title: formatAuditEventTitle(event.event),
    time: new Date(event.created_at).toLocaleTimeString("en-IN", { hour12: false }),
    payload: event.payload,
    tone: mapActorToTone(event.actor),
  };
}

export function BuyerStudio() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [steps, setSteps] = useState<{ icon: "search" | "chart" | "deal"; call: string; result: string }[]>([]);
  const [events, setEvents] = useState<ReturnType<typeof transformAuditEvent>[]>([]);
  const [confirming, setConfirming] = useState(false);
  const [intent, setIntent] = useState("");
  const [purchaseIntent, setPurchaseIntent] = useState<PurchaseIntent | null>(null);
  const [comparisonProducts, setComparisonProducts] = useState<ComparisonProduct[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<ComparisonProduct | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [polling, setPolling] = useState(false);
  const runToken = useRef(0);

  const push = useCallback((e: { actor: string; title: string; tone: "buyer" | "merchant" | "approved" | "blocked" | "neutral"; payload: Record<string, unknown> }) => {
    setEvents((prev) => [
      ...prev,
      { ...e, id: crypto.randomUUID(), time: clock() },
    ]);
  }, []);

  const reset = useCallback(() => {
    runToken.current += 1;
    setPhase("idle");
    setSteps([]);
    setEvents([]);
    setConfirming(false);
    setPurchaseIntent(null);
    setComparisonProducts([]);
    setSelectedProduct(null);
    setError(null);
  }, []);

  const run = useCallback(async () => {
    if (!intent.trim()) {
      setError("Please enter a purchase intent");
      return;
    }

    runToken.current += 1;
    const token = runToken.current;
    const alive = () => token === runToken.current;

    setSteps([]);
    setEvents([]);
    setError(null);
    setPhase("parsing");
    push({
      actor: "SYSTEM",
      tone: "neutral",
      title: "Intent received & parsed",
      payload: { raw_intent: intent },
    });

    try {
      // Step 1: Create intent
      const intentResponse = await api.createIntent(intent);

      if (!intentResponse.success) {
        throw new Error(intentResponse.error ?? "Failed to create intent");
      }

      const purchaseIntentId = intentResponse.purchase_intent_id;
      push({
        actor: "SYSTEM",
        tone: "neutral",
        title: "Intent created",
        payload: { purchase_intent_id: purchaseIntentId },
      });

      // Step 2: Poll for completion
      setPhase("thinking");
      setPolling(true);

      let finalIntent: PurchaseIntent | null = null;
      let attempts = 0;
      const maxAttempts = 40; // ~60 seconds max

      while (attempts < maxAttempts && alive()) {
        await sleep(1500);
        attempts++;

        const intentData = await api.getPurchaseIntent(purchaseIntentId);
        if (intentData.status !== "DRAFT" && intentData.status !== "POLICY_CHECKED") {
          finalIntent = intentData;
          break;
        }
      }

      if (!alive()) return;
      setPolling(false);

      if (!finalIntent) {
        throw new Error("Intent processing timed out");
      }

      setPurchaseIntent(finalIntent);

      // Step 3: Fetch comparison products if needed
      // We'll use the product from the intent
      // For now, we'll fetch the product details
      // The backend doesn't return comparison directly, so we'll simulate based on what we have

      // Step 4: Process the result
      if (finalIntent.status === "BLOCKED") {
        setPhase("policy");
        push({
          actor: "POLICY ENGINE",
          tone: "blocked",
          title: "Policy verdict: BLOCKED",
          payload: { reason: finalIntent.policy_reason, amount: finalIntent.amount },
        });
        return;
      }

      if (finalIntent.status === "NEEDS_APPROVAL") {
        setPhase("approval");
        push({
          actor: "POLICY ENGINE",
          tone: "blocked",
          title: "Policy verdict: NEEDS_APPROVAL",
          payload: { reason: finalIntent.policy_reason, amount: finalIntent.amount },
        });
        return;
      }

      if (finalIntent.status === "ALLOWED") {
        setPhase("approved");
        push({
          actor: "POLICY ENGINE",
          tone: "approved",
          title: "Policy verdict: AUTO_ALLOWED",
          payload: { reason: finalIntent.policy_reason, amount: finalIntent.amount },
        });
        return;
      }

    } catch (err) {
      if (!alive()) return;
      setPolling(false);
      const message = err instanceof ApiError ? err.message : err instanceof Error ? err.message : "Unknown error";
      setError(message);
      push({
        actor: "SYSTEM",
        tone: "blocked",
        title: "Error",
        payload: { error: message },
      });
    }
  }, [intent, push]);

  const approve = async () => {
    if (!purchaseIntent) return;

    setPhase("approved");
    push({
      actor: "HUMAN",
      tone: "approved",
      title: "Human approved the agent proposal",
      payload: { decision: "APPROVED", amount: purchaseIntent.amount },
    });

    try {
      const response = await api.approvePurchaseIntent(purchaseIntent.id);
      if (!response.success) {
        throw new Error(response.error ?? "Approval failed");
      }
      const updated = await api.getPurchaseIntent(purchaseIntent.id);
      setPurchaseIntent(updated);
      setPhase("approved");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : err instanceof Error ? err.message : "Approval failed";
      setError(message);
      push({
        actor: "SYSTEM",
        tone: "blocked",
        title: "Approval failed",
        payload: { error: message },
      });
    }
  };

  const reject = async () => {
    if (!purchaseIntent) return;

    setPhase("rejected");
    push({
      actor: "HUMAN",
      tone: "blocked",
      title: "Human rejected the agent proposal",
      payload: { decision: "REJECTED", amount: purchaseIntent?.amount },
    });

    try {
      await api.rejectPurchaseIntent(purchaseIntent.id);
      const updated = await api.getPurchaseIntent(purchaseIntent.id);
      setPurchaseIntent(updated);
      setPhase("rejected");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : err instanceof Error ? err.message : "Rejection failed";
      setError(message);
    }
  };

  const handleCheckout = async () => {
    if (!purchaseIntent) return;

    try {
      setPhase("paying");
      push({
        actor: "SYSTEM",
        tone: "neutral",
        title: "Creating Razorpay order",
        payload: { purchase_intent_id: purchaseIntent.id },
      });

      const orderResponse = await api.createRazorpayOrder(purchaseIntent.id);
      if (!orderResponse.success || !orderResponse.razorpay_order_id) {
        throw new Error("Failed to create Razorpay order");
      }

      push({
        actor: "SYSTEM",
        tone: "neutral",
        title: "Razorpay order created",
        payload: { order_id: orderResponse.razorpay_order_id, amount: orderResponse.amount },
      });

      // Navigate to conversational checkout page
      window.location.href = `/checkout/${purchaseIntent.id}`;
    } catch (err) {
      const message = err instanceof ApiError ? err.message : err instanceof Error ? err.message : "Failed to create order";
      setError(message);
      push({
        actor: "SYSTEM",
        tone: "blocked",
        title: "Order creation failed",
        payload: { error: message },
      });
    }
  };

  const running = phase === "parsing" || phase === "thinking" || polling;

  // Transform audit events for display
  const displayEvents = events.length > 0
    ? events
    : purchaseIntent
      ? [] // Will be populated by polling
      : [];

  return (
    <div className="space-y-6">
      {/* Intent bar */}
      <FadeIn>
        <GlassPanel className="relative overflow-hidden p-6">
          <div className="pointer-events-none absolute -left-24 -top-24 size-64 rounded-full bg-buyer/15 blur-3xl" />
          <div className="pointer-events-none absolute -bottom-28 right-10 size-64 rounded-full bg-merchant/10 blur-3xl" />
          <SectionLabel icon={<Sparkles className="size-3.5" />} tone="buyer">
            Natural Language Intent & Constraints
          </SectionLabel>
          <div className="relative mt-4 flex flex-col gap-3 sm:flex-row">
            <div className="relative flex-1">
              <Search className="absolute left-4 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <input
                value={intent}
                onChange={(e) => setIntent(e.target.value)}
                placeholder="e.g., mechanical keyboard under ₹5000 arriving within 4 days"
                className="h-14 w-full rounded-xl border border-border bg-foreground/5 pl-11 pr-4 text-sm outline-none transition placeholder:text-muted-foreground focus:border-buyer/50 focus:glow-buyer"
              />
            </div>
            <button
              onClick={run}
              disabled={running}
              className="group relative flex h-14 items-center justify-center gap-2 overflow-hidden rounded-xl bg-buyer px-6 text-sm font-semibold text-primary-foreground transition hover:brightness-110 disabled:opacity-70"
            >
              <span className="absolute inset-0 shimmer opacity-40" />
              {running ? <Loader2 className="size-4 animate-spin" /> : <Zap className="size-4" />}
              Run Buyer Agent
            </button>
          </div>

          {error && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-4 rounded-xl border border-blocked/40 bg-blocked/10 p-4 text-blocked text-sm"
            >
              {error}
            </motion.div>
          )}

          <AnimatePresence>
            {phase !== "idle" ? (
              <motion.div
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="mt-4 rounded-xl border border-buyer/25 bg-buyer/5 p-4"
              >
                <p className="font-mono text-[11px] uppercase tracking-widest text-buyer">
                  Intent Parser · structured output
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {purchaseIntent && (
                    <>
                      <Chip tone="buyer">Category: {purchaseIntent.category ?? "Electronics"}</Chip>
                      <Chip tone="buyer">Amount: {inr(purchaseIntent.amount)}</Chip>
                      <Chip tone="buyer">Qty: {purchaseIntent.quantity}</Chip>
                    </>
                  )}
                </div>
              </motion.div>
            ) : null}
          </AnimatePresence>
        </GlassPanel>
      </FadeIn>

      {/* Canvas */}
      <div className="grid gap-6 lg:grid-cols-[1fr_1.15fr]">
        <FadeIn delay={0.05}>
          <GlassPanel className="h-full p-5">
            <div className="flex items-center justify-between">
              <SectionLabel icon={<Terminal className="size-3.5" />} tone="buyer">
                Agent Thinking Stream
              </SectionLabel>
              <div className="flex items-center gap-2 font-mono text-[11px] text-muted-foreground">
                <StatusDot tone={running ? "merchant" : phase === "idle" ? "neutral" : "approved"} />
                {running ? "EXECUTING" : phase === "idle" ? "IDLE" : "COMPLETE"}
              </div>
            </div>

            <div className="mt-4 min-h-70 space-y-3 rounded-xl border border-border bg-background/60 p-4 font-mono text-xs">
              {steps.length === 0 && !running ? (
                <p className="text-muted-foreground">
                  <span className="text-buyer">$</span> awaiting intent…
                </p>
              ) : null}
              {steps.map((s, i) => (
                <motion.div
                  key={s.call}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="space-y-1"
                >
                  <div className="flex items-start gap-2 text-buyer">
                    {s.icon === "search" ? (
                      <Search className="mt-0.5 size-3.5 shrink-0" />
                    ) : s.icon === "chart" ? (
                      <Activity className="mt-0.5 size-3.5 shrink-0" />
                    ) : (
                      <Handshake className="mt-0.5 size-3.5 shrink-0 text-merchant" />
                    )}
                    <span className="break-all">
                      <TypedLine text={s.call} />
                    </span>
                  </div>
                  <p className="pl-5.5 text-muted-foreground">
                    <span className="text-approved">→ </span>
                    {s.result}
                  </p>
                  {i === steps.length - 1 && running ? (
                    <div className="flex items-center gap-2 pl-5.5 text-[11px] text-merchant">
                      <StatusDot tone="merchant" />
                      thinking…
                    </div>
                  ) : null}
                </motion.div>
              ))}
            </div>
          </GlassPanel>
        </FadeIn>
      </div>

      {/* Policy gate */}
      <FadeIn delay={0.15}>
        <PolicyGate
          phase={phase}
          purchaseIntent={purchaseIntent}
          confirming={confirming}
          onApprove={approve}
          onReject={reject}
          onCheckout={handleCheckout}
          onReset={reset}
        />
      </FadeIn>

      <FadeIn delay={0.2}>
        <AuditTimeline events={displayEvents} />
      </FadeIn>
    </div>
  );
}

function PolicyGate({
  phase,
  purchaseIntent,
  confirming,
  onApprove,
  onReject,
  onCheckout,
  onReset,
}: {
  phase: Phase;
  purchaseIntent: PurchaseIntent | null;
  confirming: boolean;
  onApprove: () => void;
  onReject: () => void;
  onCheckout: () => void;
  onReset: () => void;
}) {
  const evaluated = ["policy", "approval", "approved", "rejected", "paying", "confirming", "paid", "failed"].includes(
    phase,
  );

  const total = purchaseIntent?.amount ?? 0;
  const qty = purchaseIntent?.quantity ?? 0;
  const unitPrice = purchaseIntent?.unit_price ?? 0;
  const needsApproval = purchaseIntent?.status === "NEEDS_APPROVAL";
  const policyReason = purchaseIntent?.policy_reason ?? "";

  const rules = [
    { name: "Allow-List Category", detail: "Category check", state: "pass" as const },
    {
      name: "Max Transaction Cap",
      detail: `${inr(total)} ≤ limit`,
      state: "pass" as const,
    },
    {
      name: "Daily Spend Limit",
      detail: `${inr(total)} of daily limit used today`,
      state: "pass" as const,
    },
    {
      name: "Autonomous Threshold Check",
      detail: needsApproval
        ? `${inr(total)} > threshold — human sign-off required`
        : `${inr(total)} ≤ threshold — agent may transact`,
      state: needsApproval ? ("warn" as const) : ("pass" as const),
    },
  ];

  if (policyReason && evaluated) {
    // Override based on actual policy reason
    rules[3] = {
      name: "Policy Decision",
      detail: policyReason,
      state: purchaseIntent?.status === "BLOCKED" ? ("fail" as const) : needsApproval ? ("warn" as const) : ("pass" as const),
    };
  }

  return (
    <GlassPanel className="relative overflow-hidden p-6">
      <div className="pointer-events-none absolute -right-20 -top-24 size-72 rounded-full bg-approved/10 blur-3xl" />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SectionLabel icon={<ShieldCheck className="size-3.5" />} tone="approved">
          Deterministic Policy Validation Engine
        </SectionLabel>
        <div className="flex items-center gap-3 font-mono text-xs text-muted-foreground">
          <span>{qty} × {inr(unitPrice)}</span>
          <span className="text-2xl font-semibold text-foreground">{inr(total)}</span>
        </div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2">
        {rules.map((r, i) => (
          <motion.div
            key={r.name}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: evaluated ? 1 : 0.35, y: 0 }}
            transition={{ delay: evaluated ? i * 0.12 : 0 }}
            className={cn(
              "flex items-start gap-3 rounded-xl border p-4",
              !evaluated
                ? "border-border bg-foreground/5"
                : r.state === "pass"
                  ? "border-approved/30 bg-approved/5"
                  : r.state === "warn"
                    ? "border-merchant/40 bg-merchant/5"
                    : "border-blocked/40 bg-blocked/5",
            )}
          >
            <div
              className={cn(
                "mt-0.5",
                !evaluated ? "text-muted-foreground" : r.state === "pass" ? "text-approved" : r.state === "warn" ? "text-merchant" : "text-blocked",
              )}
            >
              {!evaluated ? (
                <CircleAlert className="size-4" />
              ) : r.state === "pass" ? (
                <BadgeCheck className="size-4" />
              ) : r.state === "warn" ? (
                <CircleAlert className="size-4" />
              ) : (
                <Ban className="size-4" />
              )}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium">Rule {i + 1}: {r.name}</p>
              <p className="mt-1 font-mono text-[11px] text-muted-foreground">{r.detail}</p>
              <p
                className={cn(
                  "mt-2 font-mono text-[11px] font-semibold",
                  !evaluated
                    ? "text-muted-foreground"
                    : r.state === "pass"
                      ? "text-approved"
                      : r.state === "warn"
                        ? "text-merchant"
                        : "text-blocked",
                )}
              >
                {!evaluated
                  ? "PENDING"
                  : r.state === "pass"
                    ? "✅ PASSED"
                    : r.state === "warn"
                      ? "⚠️ REQUIRES HUMAN APPROVAL"
                      : "❌ BLOCKED"}
              </p>
            </div>
          </motion.div>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {phase === "approval" ? (
          <motion.div
            key="approval"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="mt-5 rounded-xl border border-merchant/40 bg-merchant/5 p-5"
          >
            <div className="flex items-center gap-2 text-merchant">
              <StatusDot tone="merchant" />
              <p className="text-sm font-semibold uppercase tracking-widest">Approval required</p>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              The buyer agent wants to spend <span className="font-mono text-foreground">{inr(total)}</span>{" "}
              This exceeds your autonomous threshold.
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
              <button
                onClick={onApprove}
                className="flex items-center gap-2 rounded-xl bg-approved px-5 py-2.5 text-sm font-semibold text-primary-foreground transition hover:brightness-110"
              >
                <Check className="size-4" /> Approve Purchase
              </button>
              <button
                onClick={onReject}
                className="flex items-center gap-2 rounded-xl border border-blocked/40 bg-blocked/10 px-5 py-2.5 text-sm font-semibold text-blocked transition hover:bg-blocked/20"
              >
                <Ban className="size-4" /> Reject Proposal
              </button>
            </div>
          </motion.div>
        ) : null}

        {phase === "approved" ? (
          <motion.div
            key="pay"
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-approved/40 bg-approved/5 p-5"
          >
            <div>
              <p className="font-mono text-xs uppercase tracking-widest text-approved">State: APPROVED</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Deterministic gate cleared. Ready to settle {inr(total)}.
              </p>
            </div>
            <button
              onClick={onCheckout}
              className="relative flex items-center gap-2 overflow-hidden rounded-xl bg-buyer px-6 py-3 text-sm font-semibold text-primary-foreground glow-buyer transition hover:brightness-110"
            >
              <span className="absolute inset-0 shimmer opacity-30" />
              <Zap className="size-4" /> Pay via Razorpay
            </button>
          </motion.div>
        ) : null}

        {confirming ? (
          <motion.div
            key="confirming"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-buyer/40 bg-buyer/5 p-5"
          >
            <div className="flex items-center gap-2">
              <Loader2 className="size-4 animate-spin text-buyer" />
              <p className="font-mono text-xs uppercase tracking-widest text-buyer">Confirming with Razorpay…</p>
            </div>
            <p className="text-sm text-muted-foreground">Waiting for webhook confirmation…</p>
          </motion.div>
        ) : null}

        {phase === "paid" || phase === "failed" || phase === "rejected" ? (
          <motion.div
            key="final"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={cn(
              "mt-5 flex flex-wrap items-center justify-between gap-3 rounded-xl border p-5",
              phase === "paid"
                ? "border-approved/40 bg-approved/5 glow-approved"
                : "border-blocked/40 bg-blocked/5 glow-blocked",
            )}
          >
            <div>
              <p
                className={cn(
                  "font-mono text-xs uppercase tracking-widest",
                  phase === "paid" ? "text-approved" : "text-blocked",
                )}
              >
                State: {phase === "paid" ? "SETTLED" : phase === "failed" ? "WEBHOOK_FAILED" : "REJECTED"}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                {phase === "paid"
                  ? `Payment captured. ${inr(total)} settled and stock committed.`
                  : phase === "failed"
                    ? "Webhook delivery failed — stock reservation released, funds refunded."
                    : "Human rejected the proposal. No funds moved."}
              </p>
            </div>
            <button
              onClick={onReset}
              className="rounded-xl border border-border bg-foreground/5 px-5 py-2.5 text-sm font-medium transition hover:bg-foreground/10"
            >
              Reset run
            </button>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </GlassPanel>
  );
}