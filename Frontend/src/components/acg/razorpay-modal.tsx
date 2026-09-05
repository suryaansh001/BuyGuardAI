import { AnimatePresence, motion } from "motion/react";
import { CreditCard, Loader2, Lock, ShieldCheck, Smartphone, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { inr } from "@/lib/acg-data";

export function RazorpayModal({
  open,
  amount,
  orderId,
  processing,
  onClose,
  onSuccess,
}: {
  open: boolean;
  amount: number;
  orderId: string;
  processing: boolean;
  onClose: () => void;
  onSuccess: (response: {
    razorpay_order_id: string;
    razorpay_payment_id: string;
    razorpay_signature: string;
  }) => void;
}) {
  const [method, setMethod] = useState<"upi" | "card">("upi");
  const [error, setError] = useState<string | null>(null);
  const razorpayLoaded = useRef(false);

  useEffect(() => {
    if (open && !razorpayLoaded.current) {
      const script = document.createElement("script");
      script.src = "https://checkout.razorpay.com/v1/checkout.js";
      script.async = true;
      script.onload = () => {
        razorpayLoaded.current = true;
      };
      script.onerror = () => {
        setError("Failed to load Razorpay Checkout.js");
      };
      document.body.appendChild(script);
      return () => {
        document.body.removeChild(script);
      };
    }
  }, [open]);

  const handlePay = () => {
    if (!window.Razorpay) {
      setError("Razorpay Checkout.js not loaded");
      return;
    }

    const options = {
      key: import.meta.env.VITE_RAZORPAY_KEY_ID ?? "rzp_test_demo",
      amount: amount * 100, // Convert to paise
      currency: "INR",
      name: "Agent Commerce Gateway",
      description: "Test Mode Payment",
      order_id: orderId,
      handler: (response: {
        razorpay_order_id: string;
        razorpay_payment_id: string;
        razorpay_signature: string;
      }) => {
        onSuccess(response);
      },
      prefill: {
        name: "Demo Buyer",
        email: "buyer@demo.com",
        contact: "9999999999",
      },
      theme: {
        color: "#0ea5e9",
      },
      modal: {
        ondismiss: () => {
          onClose();
        },
      },
    };

    const rzp = new window.Razorpay(options);
    rzp.on("payment.failed", (response: {
      error: { code: string; description: string; source: string; step: string; reason: string };
    }) => {
      setError(`Payment failed: ${response.error.description}`);
      onClose();
    });
    rzp.open();
  };

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.94, y: 18 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 10 }}
            transition={{ type: "spring", stiffness: 260, damping: 24 }}
            className="glass w-full max-w-md overflow-hidden rounded-2xl"
          >
            <div className="flex items-center justify-between border-b border-border bg-foreground/5 px-5 py-4">
              <div className="flex items-center gap-2">
                <div className="grid size-8 place-items-center rounded-lg bg-buyer/15 text-buyer">
                  <Lock className="size-4" />
                </div>
                <div>
                  <p className="text-sm font-semibold">Razorpay Checkout</p>
                  <p className="font-mono text-[11px] text-muted-foreground">TEST MODE · {orderId}</p>
                </div>
              </div>
              <button
                onClick={onClose}
                aria-label="Close checkout"
                className="rounded-md p-1.5 text-muted-foreground transition hover:bg-foreground/10 hover:text-foreground"
              >
                <X className="size-4" />
              </button>
            </div>

            <div className="px-5 py-5">
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mb-4 rounded-xl border border-blocked/40 bg-blocked/10 p-3 text-blocked text-sm"
                >
                  {error}
                </motion.div>
              )}

              <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Amount payable</p>
              <p className="mt-1 font-mono text-4xl font-semibold text-buyer text-glow-buyer">
                {inr(amount)}
              </p>

              <div className="mt-5 grid grid-cols-2 gap-2">
                {(
                  [
                    { key: "upi", label: "UPI", icon: Smartphone },
                    { key: "card", label: "Card", icon: CreditCard },
                  ] as const
                ).map((m) => (
                  <button
                    key={m.key}
                    onClick={() => setMethod(m.key)}
                    className={cn(
                      "flex items-center gap-2 rounded-xl border px-3 py-3 text-sm transition",
                      method === m.key
                        ? "border-buyer/50 bg-buyer/10 text-buyer glow-buyer"
                        : "border-border bg-foreground/5 text-muted-foreground hover:text-foreground",
                    )}
                  >
                    <m.icon className="size-4" />
                    {m.label}
                  </button>
                ))}
              </div>

              <div className="mt-4 rounded-xl border border-border bg-foreground/5 p-3 font-mono text-xs text-muted-foreground">
                {method === "upi"
                  ? "vpa: success@razorpay (test success) | failure@razorpay (test failure)"
                  : "card: 4111 1111 1111 1111 · 12/29 · 123"}
              </div>

              <button
                disabled={processing || !razorpayLoaded.current}
                onClick={handlePay}
                className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-buyer px-4 py-3 text-sm font-semibold text-primary-foreground transition hover:brightness-110 disabled:opacity-70"
              >
                {processing ? (
                  <>
                    <Loader2 className="size-4 animate-spin" /> Processing…
                  </>
                ) : !razorpayLoaded.current ? (
                  <>
                    <Loader2 className="size-4 animate-spin" /> Loading Razorpay…
                  </>
                ) : (
                  <>
                    <ShieldCheck className="size-4" /> Pay {inr(amount)}
                  </>
                )}
              </button>
              <p className="mt-3 text-center text-[11px] text-muted-foreground">
                Test mode: use success@razorpay for success, failure@razorpay for failure
              </p>
            </div>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}

// Extend Window interface for Razorpay
declare global {
  interface Window {
    Razorpay: new (options: {
      key: string;
      amount: number;
      currency: string;
      name: string;
      description: string;
      order_id: string;
      handler: (response: {
        razorpay_order_id: string;
        razorpay_payment_id: string;
        razorpay_signature: string;
      }) => void;
      prefill: { name: string; email: string; contact: string };
      theme: { color: string };
      modal: { ondismiss: () => void };
    }) => {
      open: () => void;
      on: (event: string, callback: (response: { error: { code: string; description: string; source: string; step: string; reason: string } }) => void) => void;
    };
  }
}