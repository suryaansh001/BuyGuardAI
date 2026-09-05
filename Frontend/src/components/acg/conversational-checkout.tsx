import { AnimatePresence, motion } from "motion/react";
import { 
  CreditCard, 
  Loader2, 
  Lock, 
  ShieldCheck, 
  Smartphone, 
  X, 
  MessageSquare,
  Sparkles,
  ArrowRight,
  CheckCircle,
  AlertCircle,
  ExternalLink,
  Send,
  Search,
  Star,
  Tag,
  RotateCcw,
  Info
} from "lucide-react";
import { useEffect, useRef, useState, useCallback } from "react";
import { cn } from "@/lib/utils";
import { inr } from "@/lib/acg-data";
import { api, ApiError } from "@/lib/api";
import { EmbeddedRazorpayCheckout } from "./embedded-razorpay-checkout";
import { GlassPanel, SectionLabel, Chip, StatusDot } from "./primitives";

interface ConversationalCheckoutProps {
  purchaseIntent: {
    id: number;
    amount: number;
    unit_price: number;
    quantity: number;
    status: string;
    product: {
      id: number;
      name: string;
      merchant: string;
      category: string;
    };
    merchant: {
      id: number;
      name: string;
    };
    razorpay_order_id?: string;
    razorpay_key_id?: string;
  };
  onClose: () => void;
  onSuccess: (response: {
    razorpay_order_id: string;
    razorpay_payment_id: string;
    razorpay_signature: string;
  }) => void;
}

interface ChatMessage {
  id: string;
  role: "assistant" | "user" | "system";
  content: string;
  type?: "text" | "product" | "payment" | "confirmation" | "error";
  metadata?: Record<string, any>;
  timestamp: Date;
}

interface CheckoutStep {
  id: string;
  label: string;
  status: "pending" | "active" | "completed" | "error";
}

const CHECKOUT_STEPS: CheckoutStep[] = [
  { id: "cart", label: "Cart Review", status: "pending" },
  { id: "details", label: "Delivery Details", status: "pending" },
  { id: "payment", label: "Payment", status: "pending" },
  { id: "confirmation", label: "Confirmation", status: "pending" },
];

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function formatTime(date: Date) {
  return date.toLocaleTimeString("en-IN", { hour12: false });
}

function TypedLine({ text, speed = 15 }: { text: string; speed?: number }) {
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
    }, speed);
    return () => clearInterval(id);
  }, [text, speed]);
  return <span>{text.slice(0, n)}</span>;
}

function renderCheckoutContent({
  showConfirmation,
  error,
  showPayment,
  purchaseIntent,
  handleClose,
  setShowConfirmation,
  setShowPayment,
  setPaymentError,
  setPaymentResult,
}: {
  showConfirmation: boolean;
  error: string | null;
  showPayment: boolean;
  purchaseIntent: any;
  handleClose: () => void;
  setShowConfirmation: (v: boolean) => void;
  setShowPayment: (v: boolean) => void;
  setPaymentError: (e: string | null) => void;
  setPaymentResult: (r: any) => void;
}) {
  if (showConfirmation) {
    return (
      <motion.div
        key="confirmation"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        className="border-t border-border/50 px-5 py-4"
      >
        <div className="text-center">
          <CheckCircle className="size-12 text-approved mx-auto mb-3" />
          <p className="text-lg font-semibold mb-1">Order Confirmed!</p>
          <p className="text-sm text-muted-foreground mb-4">Your order has been placed successfully.</p>
          <button
            onClick={handleClose}
            className="w-full rounded-xl bg-buyer px-4 py-2.5 text-sm font-semibold text-primary-foreground transition hover:brightness-110"
          >
            Done
          </button>
        </div>
      </motion.div>
      );
    } else if (error) {
      return (
        <motion.div
          key="error"
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="border-t border-blocked/50 px-5 py-3"
        >
          <div className="rounded-xl border border-blocked/40 bg-blocked/10 p-3 text-blocked text-sm">
            {error}
          </div>
        </motion.div>
      );
    } else if (showPayment && !showConfirmation && !error) {
      return (
        <motion.div
          key="payment"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          className="border-t border-border/50 px-5 py-4"
        >
          <EmbeddedRazorpayCheckout
            amount={purchaseIntent?.amount ?? 0}
            orderId={purchaseIntent.razorpay_order_id || ""}
            keyId={import.meta.env.VITE_RAZORPAY_KEY_ID ?? "rzp_test_demo"}
            simulationMode={purchaseIntent.razorpay_order_id?.startsWith("order_mock_") ?? false}
            onSuccess={(response) => {
              setShowConfirmation(true);
              setShowPayment(false);
            }}
            onClose={() => {
              setShowPayment(false);
            }}
            onError={(error) => {
              // setPaymentError(error);
            }}
          />
        </motion.div>
      );
    } else {
      return null;
    }
  }

export function ConversationalCheckout({
  purchaseIntent,
  onClose,
  onSuccess,
}: ConversationalCheckoutProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPayment, setShowPayment] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [paymentResult, setPaymentResult] = useState<{
    razorpay_order_id: string;
    razorpay_payment_id: string;
    razorpay_signature: string;
  } | null>(null);
  const [paymentError, setPaymentError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const [comparisonProducts, setComparisonProducts] = useState<any[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<any>(null);
  const [polling, setPolling] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [isAIResponding, setIsAIResponding] = useState(false);
  const runToken = useRef(0);

  const handleClose = useCallback(() => {
    onClose();
  }, [onClose]);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Fetch similar products for comparison
  useEffect(() => {
    if (purchaseIntent.product?.category) {
      api.getRecommendations(purchaseIntent.product.category, purchaseIntent.id)
        .then((res: any) => {
          if (res.products) {
            setComparisonProducts(res.products.slice(0, 3));
          }
        })
        .catch(() => {});
    }
  }, [purchaseIntent]);

  const handleUserResponse = useCallback((response: string) => {
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: response,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setChatInput("");

    if (response === "Confirm address") {
      setTimeout(() => {
        const paymentMessage: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: "Great! Now let's proceed to payment. Your order is ready for checkout.",
          type: "payment",
          metadata: { action: "confirm_payment" },
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, paymentMessage]);
      }, 500);
    }
  }, []);

  // AI chat handler for product questions
  const handleAIChat = useCallback(async (question: string) => {
    if (!question.trim() || isAIResponding) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: question,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setChatInput("");
    setIsAIResponding(true);

    try {
      // Call AI agent endpoint with product context
      const response = await api.chatWithAgent({
        question,
        productId: purchaseIntent.product?.id,
        productName: purchaseIntent.product?.name,
        merchantName: purchaseIntent.product?.merchant || purchaseIntent.merchant?.name,
        category: purchaseIntent.product?.category,
        specs: purchaseIntent.product?.specs,
        comparisonProducts: comparisonProducts.map(p => ({
          name: p.name,
          price: p.price,
          merchant: p.merchant,
          specs: p.specs,
        })),
      });

      const aiMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: response.answer || "I'm not sure about that. Let me know if you have other questions!",
        type: response.type || "text",
        metadata: response.metadata,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, aiMessage]);
    } catch (err) {
      const errorMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "Sorry, I couldn't process that question. Please try again.",
        type: "error",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsAIResponding(false);
    }
  }, [isAIResponding, purchaseIntent, comparisonProducts]);

  useEffect(() => {
    const initialMessages: ChatMessage[] = [
      {
        id: crypto.randomUUID(),
        role: "assistant",
        content: `Welcome to Agent Commerce Gateway! I've found a great match for your purchase intent. You can ask me anything about this product - features, reviews, comparisons, or alternatives.`,
        type: "text",
        timestamp: new Date(),
      },
      {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "",
        type: "product",
        metadata: {
          product: {
            name: purchaseIntent.product?.name || "Selected Product",
            merchant: purchaseIntent.product?.merchant || purchaseIntent.merchant?.name || "Unknown Merchant",
            price: purchaseIntent.amount || 0,
            specs: purchaseIntent.product?.specs || {},
          },
        },
        timestamp: new Date(Date.now() + 100),
      },
      {
        id: crypto.randomUUID(),
        role: "assistant",
        content: `Your order: **${purchaseIntent.product?.name}** from **${purchaseIntent.product?.merchant || purchaseIntent.merchant?.name}** for **₹${(purchaseIntent.amount || 0).toLocaleString()}**\n\nYou can ask me about:\n• Product features & specifications\n• Reviews & ratings\n• Similar alternatives & comparisons\n• Delivery & warranty info\n\nOr confirm your delivery address to proceed.`,
        type: "text",
        metadata: { action: "confirm_address" },
        timestamp: new Date(Date.now() + 200),
      },
    ];
    setMessages(initialMessages);
  }, [purchaseIntent]);

  const handlePaymentSuccess = useCallback((response: {
    razorpay_order_id: string;
    razorpay_payment_id: string;
    razorpay_signature: string;
  }) => {
    setShowConfirmation(true);
    setShowPayment(false);
    const confirmMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "system",
      content: `✅ Payment successful! Order ID: ${response.razorpay_order_id}, Payment ID: ${response.razorpay_payment_id}`,
      type: "confirmation",
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, confirmMessage]);
    onSuccess(response);
  }, [onSuccess]);

  const handlePaymentClose = useCallback(() => {
    setShowPayment(false);
  }, []);

  const handlePaymentError = useCallback((err: string) => {
    setError(err);
    setShowPayment(false);
  }, []);

  const handleSendMessage = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (chatInput.trim()) {
      handleAIChat(chatInput.trim());
    }
  }, [chatInput, handleAIChat]);

  const handleQuickQuestion = useCallback((question: string) => {
    handleAIChat(question);
  }, [handleAIChat]);

  return (
    <AnimatePresence>
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
          className="glass w-full max-w-2xl overflow-hidden rounded-2xl max-h-[90vh]"
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-border bg-foreground/5 px-5 py-4">
            <div className="flex items-center gap-2">
              <div className="grid size-8 place-items-center rounded-lg bg-buyer/15 text-buyer">
                <Sparkles className="size-4" />
              </div>
              <div>
                <p className="text-sm font-semibold">Conversational Checkout</p>
                <p className="font-mono text-[11px] text-muted-foreground">Agent Commerce Gateway</p>
              </div>
            </div>
          </div>

          {/* Chat Area */}
          <div className="flex-1 overflow-y-auto p-5 space-y-4" ref={messagesContainerRef}>
            <div ref={messagesEndRef} />
            <AnimatePresence initial={false}>
              {messages.map((msg, index) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: index * 0.1 }}
                  className="flex gap-3"
                >
                  <div className={cn(
                    "flex-shrink-0 size-8 rounded-full flex items-center justify-center text-xs font-medium",
                    msg.role === "assistant" && "bg-buyer/10 text-buyer",
                    msg.role === "user" && "bg-merchant/10 text-merchant",
                    msg.role === "system" && "bg-approved/10 text-approved",
                  )}>
                    {msg.role === "assistant" && <Sparkles className="size-4" />}
                    {msg.role === "user" && <MessageSquare className="size-4" />}
                    {msg.role === "system" && <ShieldCheck className="size-4" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 text-[11px] text-muted-foreground mb-1">
                      <span className="font-mono">{formatTime(msg.timestamp)}</span>
                      <span className="font-mono text-[10px] uppercase tracking-wider">
                        {msg.role === "assistant" ? "ASSISTANT" : msg.role === "user" ? "YOU" : "SYSTEM"}
                      </span>
                    </div>
                    <div className={cn(
                      "prose prose-sm max-w-none",
                      msg.type === "product" && "bg-buyer/5 border border-buyer/20 rounded-xl p-3",
                      msg.type === "payment" && "bg-buyer/5 border border-buyer/20 rounded-xl p-3",
                      msg.type === "confirmation" && "bg-approved/5 border border-approved/20 rounded-xl p-3",
                      msg.type === "error" && "bg-blocked/5 border border-blocked/20 rounded-xl p-3",
                    )}>
                      <TypedLine text={msg.content} />
                      {msg.metadata?.product && (
                        <div className="mt-3 p-3 bg-background/50 rounded-lg border border-border/50">
                          <div className="flex items-start gap-3">
                            <div className="size-16 rounded-lg bg-buyer/10 flex items-center justify-center">
                              <Sparkles className="size-5 text-buyer" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="font-semibold text-sm">{msg.metadata.product.name}</p>
                              <p className="text-xs text-muted-foreground">{msg.metadata.product.merchant}</p>
                              <p className="mt-1 font-mono text-sm text-buyer">{inr(msg.metadata.product.price)}</p>
                              <div className="mt-2 flex flex-wrap gap-1">
                                {msg.metadata.product.specs?.ports?.map((port: string, i: number) => (
                                  <Chip key={i} tone="neutral" size="sm">{port}</Chip>
                                ))}
                              </div>
                            </div>
                          </div>
                        </div>
                      )}
                      {msg.metadata?.action === "confirm_address" && (
                        <div className="mt-3">
                          <button
                            onClick={() => handleUserResponse("Confirm address")}
                            className="w-full rounded-xl bg-buyer px-4 py-2.5 text-sm font-semibold text-primary-foreground transition hover:brightness-110"
                          >
                            <CheckCircle className="size-4 inline mr-2" /> Confirm & Continue
                          </button>
                        </div>
                      )}
                      {msg.metadata?.action === "confirm_payment" && (
                        <div className="mt-3 space-y-2">
                          <button
                            onClick={() => setShowPayment(true)}
                            className="w-full rounded-xl bg-buyer px-4 py-3 text-sm font-semibold text-primary-foreground glow-buyer transition hover:brightness-110"
                          >
                            <ShieldCheck className="size-4 inline mr-2" /> Proceed to Payment
                          </button>
                        </div>
                      )}
                    </div>
                    <p className="font-mono text-[11px] text-muted-foreground mt-1">{formatTime(msg.timestamp)}</p>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>

          {/* Input Area */}
          <AnimatePresence mode="wait">
            {showConfirmation ? (
              <motion.div
                key="confirmation"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="border-t border-border/50 px-5 py-4"
              >
                <div className="text-center">
                  <CheckCircle className="size-12 text-approved mx-auto mb-3" />
                  <p className="text-lg font-semibold mb-1">Order Confirmed!</p>
                  <p className="text-sm text-muted-foreground mb-4">Your order has been placed successfully.</p>
                  <button
                    onClick={handleClose}
                    className="w-full rounded-xl bg-buyer px-4 py-2.5 text-sm font-semibold text-primary-foreground transition hover:brightness-110"
                  >
                    Done
                  </button>
                </div>
              </motion.div>
              ) : error ? (
                <motion.div
                  key="error"
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="border-t border-blocked/50 px-5 py-3"
                >
                  <div className="rounded-xl border border-blocked/40 bg-blocked/10 p-3 text-blocked text-sm">
                    {error}
                  </div>
                </motion.div>
              ) : showPayment && !showConfirmation && !error ? (
                <motion.div
                  key="payment"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="border-t border-border/50 px-5 py-4"
                >
                  <EmbeddedRazorpayCheckout
                    amount={purchaseIntent?.amount ?? 0}
                    orderId={purchaseIntent.razorpay_order_id || ""}
                    keyId={import.meta.env.VITE_RAZORPAY_KEY_ID ?? "rzp_test_demo"}
                    simulationMode={purchaseIntent.razorpay_order_id?.startsWith("order_mock_") ?? false}
                    onSuccess={handlePaymentSuccess}
                    onClose={handlePaymentClose}
                    onError={handlePaymentError}
                  />
                </motion.div>
              ) : (
                <motion.div
                  key="chat-input"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  className="border-t border-border/50 p-4 space-y-3"
                >
                  {/* Quick Action Buttons */}
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => handleQuickQuestion("What are the key features and specifications?")}
                      disabled={isAIResponding}
                      className="text-xs px-3 py-1.5 rounded-full border border-border/50 hover:border-buyer/50 hover:bg-buyer/5 transition disabled:opacity-50"
                    >
                      <Info className="size-3 inline mr-1" /> Features
                    </button>
                    <button
                      onClick={() => handleQuickQuestion("What do reviews say about this product?")}
                      disabled={isAIResponding}
                      className="text-xs px-3 py-1.5 rounded-full border border-border/50 hover:border-buyer/50 hover:bg-buyer/5 transition disabled:opacity-50"
                    >
                      <Star className="size-3 inline mr-1" /> Reviews
                    </button>
                    <button
                      onClick={() => handleQuickQuestion("Show me similar alternatives with comparison")}
                      disabled={isAIResponding}
                      className="text-xs px-3 py-1.5 rounded-full border border-border/50 hover:border-buyer/50 hover:bg-buyer/5 transition disabled:opacity-50"
                    >
                      <RotateCcw className="size-3 inline mr-1" /> Compare
                    </button>
                    <button
                      onClick={() => handleQuickQuestion("What's the delivery time and warranty?")}
                      disabled={isAIResponding}
                      className="text-xs px-3 py-1.5 rounded-full border border-border/50 hover:border-buyer/50 hover:bg-buyer/5 transition disabled:opacity-50"
                    >
                      <Tag className="size-3 inline mr-1" /> Delivery
                    </button>
                  </div>

                  {/* Chat Input */}
                  <form onSubmit={handleSendMessage} className="flex gap-2">
                    <input
                      type="text"
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      placeholder={isAIResponding ? "AI is thinking..." : "Ask about features, reviews, comparisons..."}
                      disabled={isAIResponding}
                      className="flex-1 px-4 py-2.5 rounded-xl border border-border/50 bg-background/50 text-sm focus:border-buyer focus:outline-none focus:ring-1 focus:ring-buyer disabled:opacity-50"
                    />
                    <button
                      type="submit"
                      disabled={!chatInput.trim() || isAIResponding}
                      className="px-4 py-2.5 rounded-xl bg-buyer text-primary-foreground text-sm font-medium hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                    >
                      <Send className="size-4" />
                      {isAIResponding && <Loader2 className="size-4 animate-spin" />}
                    </button>
                  </form>

                  {/* Similar Products Comparison */}
                  {comparisonProducts.length > 0 && (
                    <div className="pt-2 border-t border-border/50">
                      <p className="text-xs font-semibold text-muted-foreground mb-2">Similar Options</p>
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                        {comparisonProducts.map((p: any, i: number) => (
                          <button
                            key={p.id || i}
                            onClick={() => handleQuickQuestion(`Compare with ${p.name} from ${p.merchant}`)}
                            disabled={isAIResponding}
                            className="text-left p-3 rounded-lg border border-border/50 hover:border-buyer/50 hover:bg-buyer/5 transition disabled:opacity-50"
                          >
                            <p className="font-medium text-sm truncate">{p.name}</p>
                            <p className="text-xs text-muted-foreground">{p.merchant}</p>
                            <p className="mt-1 font-mono text-sm text-buyer">{inr(p.price || 0)}</p>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </motion.div>
              )}
          </AnimatePresence>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

export default ConversationalCheckout;