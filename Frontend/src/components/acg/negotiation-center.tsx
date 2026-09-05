import { motion } from "motion/react";
import { useEffect, useState } from "react";
import { Braces, Code2, Gauge, Radio, ShieldAlert, Table2, Send, RefreshCw, Loader2, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { inr } from "@/lib/acg-data";
import { api } from "@/lib/api";
import { AnimatedCounter, Chip, FadeIn, GlassPanel, SectionLabel, StatusDot } from "./primitives";
import type { Product } from "@/lib/types";

const accentText = {
  buyer: "text-buyer",
  merchant: "text-merchant",
  approved: "text-approved",
} as const;

export function NegotiationCenter() {
  const [view, setView] = useState<"form" | "history">("form");
  const [products, setProducts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [negotiating, setNegotiating] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);

  const [formData, setFormData] = useState({
    product_id: "",
    quantity: 1,
    offered_price: "",
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [catalogData, productsData] = await Promise.all([
          api.getMerchantCatalog(1).catch(() => null),
        ]);

        if (catalogData) {
          const transformedProducts = catalogData.catalog.map((p) => ({
            id: parseInt(p.sku.replace("p", "")) || 0,
            name: p.title,
            merchantId: "m_tech",
            merchant: catalogData.merchant,
            category: p.category,
            base_price: p.base_price,
            currency: p.currency,
            delivery_days: p.delivery_sla_days,
            stock: p.stock,
            spec: {},
            pricing_tiers: Object.entries(p.pricing_tiers).map(([key, value]) => {
              const [minQty] = key.split("-");
              return { minQty: parseInt(minQty) || 1, unitPrice: value };
            }),
            score: 90,
          }));
          setProducts(transformedProducts);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to fetch data");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleNegotiate = async () => {
    if (!formData.product_id || !formData.quantity) return;
    
    setNegotiating(true);
    setError(null);
    setResult(null);

    try {
      const result = await api.negotiate({
        product_id: parseInt(formData.product_id),
        quantity: parseInt(formData.quantity),
        offered_price: formData.offered_price ? parseInt(formData.offered_price) : undefined,
      });
      
      setResult(result);
      // Refresh history
      fetchHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Negotiation failed");
    } finally {
      setNegotiating(false);
    }
  };

  const fetchHistory = async () => {
    try {
      // We'll fetch from the negotiations endpoint
      // This would need a new API endpoint, for now we'll use a mock
      // In production, you'd add GET /api/negotiations/history
    } catch (err) {
      console.error("Failed to fetch history:", err);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleNegotiate();
  };

  const selectedProduct = products.find(p => p.id === parseInt(formData.product_id));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-3">
          <div className="grid size-10 place-items-center rounded-xl border border-merchant/30 bg-merchant/10 text-merchant">
            <Gauge className="size-5" />
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-tight sm:text-base">
              Live Negotiation Terminal
            </h1>
            <p className="font-mono text-[11px] text-muted-foreground">
              POST /api/negotiate · Real-time bulk pricing
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 ml-auto">
          <button
            onClick={() => setView(v => v === "form" ? "history" : "form")}
            className={cn(
              "rounded-xl border px-3 py-2 text-xs font-medium transition",
              view === "form"
                ? "text-merchant border-merchant/40 bg-merchant/10"
                : "text-muted-foreground hover:text-foreground border-border"
            )}
          >
            {view === "form" ? "Negotiate" : "History"}
          </button>
        </div>
      </div>

      {view === "form" ? (
        <FadeIn>
          <GlassPanel className="p-5">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div className="space-y-1.5">
                  <label className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Product</label>
                  <select
                    value={formData.product_id}
                    onChange={(e) => setFormData(prev => ({ ...prev, product_id: e.target.value }))}
                    className="w-full rounded-xl border border-border bg-foreground/5 px-3 py-2.5 text-sm outline-none transition hover:border-merchant/50 focus:border-merchant/50"
                  >
                    <option value="">Select a product</option>
                    {products.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} — {inr(p.base_price)}
                      </option>
                    ))}
                    </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Quantity</label>
                  <input
                    type="number"
                    min="1"
                    value={formData.quantity}
                    onChange={(e) => setFormData(prev => ({ ...prev, quantity: parseInt(e.target.value) || 1 }))}
                    className="w-full rounded-xl border border-border bg-foreground/5 px-3 py-2.5 text-sm outline-none transition hover:border-merchant/50 focus:border-merchant/50"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Offered Price (₹)</label>
                  <input
                    type="number"
                    placeholder="Optional - leave empty for tier price"
                    value={formData.offered_price}
                    onChange={(e) => setFormData(prev => ({ ...prev, offered_price: e.target.value }))}
                    className="w-full rounded-xl border border-border bg-foreground/5 px-3 py-2.5 text-sm outline-none transition hover:border-merchant/50 focus:border-merchant/50"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Base Price</label>
                  <div className="rounded-xl border border-border bg-foreground/5 px-3 py-2.5 text-sm text-muted-foreground">
                    {selectedProduct ? inr(selectedProduct.base_price) : "Select a product"}
                  </div>
                </div>
              </div>

              {result && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={cn(
                    "rounded-xl border p-4 font-mono text-xs",
                    result.success
                      ? "border-approved/30 bg-approved/5"
                      : "border-blocked/30 bg-blocked/5"
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-muted-foreground">Result</span>
                    <Chip tone={result.success ? "approved" : "blocked"}>
                      {result.success ? "SUCCESS" : "FAILED"}
                    </Chip>
                  </div>
                  <div className="mt-3 space-y-1.5 text-muted-foreground font-mono text-xs">
                    {result.unit_price && (
                      <div className="flex justify-between">
                        <span>Counter Price</span>
                        <span className="text-foreground">{inr(result.unit_price)}</span>
                      </div>
                    )}
                    {result.quantity && (
                      <div className="flex justify-between">
                        <span>Quantity</span>
                        <span className="text-foreground">{result.quantity}</span>
                      </div>
                    )}
                    {result.countered !== undefined && (
                      <div className="flex justify-between">
                        <span>Countered</span>
                        <span className={result.countered ? "text-approved" : "text-blocked"}>
                          {result.countered ? "YES" : "NO"}
                        </span>
                      </div>
                    )}
                    {result.message && (
                      <div className="flex justify-between">
                        <span>Message</span>
                        <span>{result.message}</span>
                      </div>
                    )}
                    {result.error && (
                      <div className="flex justify-between text-blocked">
                        <span>Error</span>
                        <span>{result.error}</span>
                      </div>
                    )}
                  </div>
                </motion.div>
              )}

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={negotiating || !formData.product_id}
                  className={cn(
                    "w-full flex items-center justify-center gap-2 rounded-xl bg-buyer px-4 py-3 text-sm font-semibold text-primary-foreground transition hover:brightness-110 disabled:opacity-70",
                    negotiating && "opacity-70 cursor-not-allowed"
                  )}
                >
                  {negotiating ? (
                    <>
                      <Loader2 className="size-4 animate-spin" /> Negotiating…
                    </>
                  ) : (
                    <>
                      <Send className="size-4" /> Request Negotiation
                    </>
                  )}
                </button>
              </div>
            </form>
          </GlassPanel>
        </FadeIn>
      ) : (
        <FadeIn>
          <GlassPanel className="p-5">
            <div className="flex items-center justify-between mb-4">
              <SectionLabel icon={<Braces className="size-3.5" />} tone="merchant">
                Negotiation History
              </SectionLabel>
              <button
                onClick={fetchHistory}
                disabled={loading}
                className="flex items-center gap-2 rounded-xl border border-border bg-foreground/5 px-3 py-2 text-xs font-medium transition hover:text-foreground"
              >
                <RefreshCw className={loading ? "size-4 animate-spin" : "size-4"} />
                Refresh
              </button>
            </div>
            {history.length === 0 ? (
              <div className="text-center text-muted-foreground py-8">
                <Braces className="size-12 mx-auto text-muted-foreground/50" />
                <p className="mt-2 text-sm">No negotiation history yet</p>
                <p className="text-xs mt-1">Submit a negotiation to see history here</p>
              </div>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-border">
                <table className="w-full text-left text-sm">
                  <thead className="bg-foreground/5 text-[11px] uppercase tracking-wider text-muted-foreground">
                    <tr>
                      <th className="px-4 py-3 font-medium">Product</th>
                      <th className="px-4 py-3 font-medium">Qty</th>
                      <th className="px-4 py-3 font-medium">Offered</th>
                      <th className="px-4 py-3 font-medium">Countered</th>
                      <th className="px-4 py-3 font-medium">Status</th>
                      <th className="px-4 py-3 font-medium">Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((h) => (
                      <tr key={h.id} className="border-t border-border transition hover:bg-foreground/5">
                        <td className="px-4 py-3 font-medium">{h.product_name}</td>
                        <td className="px-4 py-3 font-mono">{h.requested_qty}</td>
                        <td className="px-4 py-3 font-mono">{h.offered_price ? inr(h.offered_price) : "Tier price"}</td>
                        <td className="px-4 py-3 font-mono">{h.countered_price ? inr(h.countered_price) : "—"}</td>
                        <td className="px-4 py-3">
                          <Chip tone={h.accepted ? "approved" : h.accepted === false ? "blocked" : "merchant"}>
                            {h.accepted === true ? "ACCEPTED" : h.accepted === false ? "REJECTED" : "PENDING"}
                          </Chip>
                        </td>
                        <td className="px-4 py-3 font-mono text-[11px] text-muted-foreground">
                          {new Date(h.created_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            </GlassPanel>
          </FadeIn>
        )}
    </div>
  );
}