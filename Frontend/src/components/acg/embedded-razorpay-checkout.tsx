import { useEffect, useRef, useState, useMemo } from "react";
import { motion } from "motion/react";
import { cn } from "@/lib/utils";
import { inr } from "@/lib/acg-data";
import { Loader2, CreditCard, Smartphone, ShieldCheck, X, CheckCircle, AlertCircle, Lock } from "lucide-react";

interface EmbeddedRazorpayCheckoutProps {
  amount: number;
  orderId: string;
  keyId: string;
  onSuccess: (response: {
    razorpay_order_id: string;
    razorpay_payment_id: string;
    razorpay_signature: string;
  }) => void;
  onClose: () => void;
  onError?: (error: string) => void;
  simulationMode?: boolean; // For demo/testing without real Razorpay
}

export function EmbeddedRazorpayCheckout({
  amount,
  orderId,
  keyId,
  onSuccess,
  onClose,
  onError,
  simulationMode = false,
}: EmbeddedRazorpayCheckoutProps) {
  const [method, setMethod] = useState<"upi" | "card" | "netbanking" | "wallet">("upi");
  const [error, setError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [simulationStep, setSimulationStep] = useState<"idle" | "processing" | "success" | "failed">("idle");
  const razorpayLoaded = useRef(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Memoize simulation detection to prevent unnecessary re-renders
  const isSimulation = useMemo(
    () => simulationMode || (orderId ? orderId.startsWith("order_mock_") : false),
    [simulationMode, orderId]
  );

  // Only load Razorpay script if NOT in simulation mode AND orderId exists
  useEffect(() => {
    if (isSimulation || !orderId) {
      console.log("[Razorpay] Simulation mode or no orderId - skipping Razorpay load");
      return;
    }
    
    if (!razorpayLoaded.current) {
      console.log("[Razorpay] Loading Razorpay Checkout.js");
      const script = document.createElement("script");
      script.src = "https://checkout.razorpay.com/v1/checkout.js";
      script.async = true;
      script.onload = () => {
        razorpayLoaded.current = true;
        console.log("[Razorpay] Checkout.js loaded successfully");
      };
      script.onerror = () => {
        console.error("[Razorpay] Failed to load Razorpay Checkout.js");
      };
      document.body.appendChild(script);
      return () => {
        const existingScript = document.querySelector('script[src="https://checkout.razorpay.com/v1/checkout.js"]');
        if (existingScript) {
          document.body.removeChild(existingScript);
        }
      };
    }
  }, [isSimulation, orderId]);

  const handlePay = () => {
    if (isSimulation) {
      console.log("[Razorpay] Simulation mode - starting fake payment flow");
      // Simulation mode - fake payment flow
      setProcessing(true);
      setError(null);
      setSimulationStep("processing");
      
      // Simulate processing delay
      setTimeout(() => {
        setSimulationStep("success");
        // Simulate successful payment response
        const mockResponse = {
          razorpay_order_id: orderId,
          razorpay_payment_id: `pay_mock_${Math.random().toString(36).substring(2, 15)}`,
          razorpay_signature: `sig_mock_${Math.random().toString(36).substring(2, 15)}`,
        };
        setTimeout(() => {
          onSuccess(mockResponse);
        }, 800);
      }, 1500);
      return;
    }

    if (!window.Razorpay) {
      setError("Razorpay Checkout.js not loaded");
      return;
    }

    setProcessing(true);
    setError(null);

    const options = {
      key: keyId,
      amount: amount,
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
      const errorMsg = `Payment failed: ${response.error.description}`;
      setError(errorMsg);
      setProcessing(false);
    });
    rzp.open();
    setProcessing(false);
  };

  return (
    <div className="glass w-full overflow-hidden rounded-2xl">
      <div className="flex items-center justify-between border-b border-border bg-foreground/5 px-5 py-4">
        <div className="flex items-center gap-2">
          <div className="grid size-8 place-items-center rounded-lg bg-buyer/15 text-buyer">
            <Lock className="size-4" />
          </div>
          <div>
            <p className="text-sm font-semibold">Secure Payment</p>
            <p className="font-mono text-[11px] text-muted-foreground">
              {isSimulation ? "SIMULATION MODE" : "TEST MODE"} · {orderId}
            </p>
          </div>
        </div>

        <div className="px-5 py-5">
          {error && (
            <div className="mb-4 rounded-xl border border-blocked/40 bg-blocked/10 p-3 text-blocked text-sm">
              {error}
            </div>
          )}

          <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Amount payable</p>
          <p className="mt-1 font-mono text-4xl font-semibold text-buyer text-glow-buyer">
            {inr(amount)}
          </p>

          {isSimulation && simulationStep !== "idle" && (
            <AnimatePresence mode="wait">
              {simulationStep === "processing" && (
                <motion.div
                  key="processing"
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                  className="mt-4 flex flex-col items-center gap-3 p-4 rounded-xl bg-buyer/10 border border-buyer/20"
                >
                  <Loader2 className="size-8 animate-spin text-buyer" />
                  <p className="text-buyer font-medium">Processing payment...</p>
                  <p className="text-xs text-muted-foreground">Simulating Razorpay checkout flow</p>
                </motion.div>
              )}
              {simulationStep === "success" && (
                <motion.div
                  key="success"
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  className="mt-4 flex flex-col items-center gap-3 p-4 rounded-xl bg-approved/10 border border-approved/20"
                >
                  <CheckCircle className="size-8 text-approved" />
                  <p className="text-approved font-medium">Payment Successful!</p>
                  <p className="text-xs text-muted-foreground">Redirecting to confirmation...</p>
                </motion.div>
              )}
            </AnimatePresence>
          )}

          {!isSimulation || simulationStep === "idle" ? (
            <>
              <div className="mt-5 grid grid-cols-3 gap-2">
                {([
                  { key: "upi", label: "UPI", icon: Smartphone },
                  { key: "card", label: "Card", icon: CreditCard },
                  { key: "netbanking", label: "NetBanking", icon: ShieldCheck },
                ] as const).map((m) => (
                  <button
                    key={m.key}
                    onClick={() => setMethod(m.key)}
                    className={cn(
                      "flex flex-col items-center gap-2 rounded-xl border px-3 py-3 text-sm transition",
                      method === m.key
                        ? "border-buyer/50 bg-buyer/10 text-buyer glow-buyer"
                        : "border-border bg-foreground/5 text-muted-foreground hover:text-foreground",
                    )}
                  >
                    <m.icon className="size-5" />
                    <span className="font-medium">{m.label}</span>
                  </button>
                ))}
              </div>

              <div className="mt-4 rounded-xl border border-border bg-foreground/5 p-3 font-mono text-xs text-muted-foreground">
                {method === "upi"
                  ? "vpa: success@razorpay (test success) | failure@razorpay (test failure)"
                  : method === "card"
                  ? "card: 4111 1111 1111 1111 · 12/29 · 123"
                  : "netbanking: Select your bank from the list"}
              </div>

              <button
                disabled={processing || (!isSimulation && !razorpayLoaded.current)}
                onClick={handlePay}
                className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-buyer px-4 py-3 text-sm font-semibold text-primary-foreground transition hover:brightness-110 disabled:opacity-70"
              >
                {processing ? (
                  <>
                    <Loader2 className="size-4 animate-spin" /> Processing…
                  </>
                ) : !isSimulation && !razorpayLoaded.current ? (
                  <>
                    <Loader2 className="size-4 animate-spin" /> Loading Razorpay…
                  </>
                ) : isSimulation ? (
                  <>
                    <ShieldCheck className="size-4" /> Simulate Payment {inr(amount)}
                  </>
                ) : (
                  <>
                    <ShieldCheck className="size-4" /> Pay {inr(amount)}
                  </>
                )}
              </button>
            </>
          ) : null}

          {error && !isSimulation && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-4 rounded-xl border border-blocked/40 bg-blocked/10 p-3 text-blocked text-sm"
            >
              {error}
            </motion.div>
          )}

          <p className="mt-3 text-center text-[11px] text-muted-foreground">
            {isSimulation
              ? "Simulation mode: click button to simulate successful payment"
              : "Test mode: use success@razorpay for success, failure@razorpay for failure"}
          </p>
        </div>
      </div>
    </div>
  );
}