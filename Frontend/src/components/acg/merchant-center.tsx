import { motion } from "motion/react";
import { Braces, Code2, Gauge, Radio, ShieldAlert, Table2 } from "lucide-react";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { inr } from "@/lib/acg-data";
import { AnimatedCounter, Chip, FadeIn, GlassPanel, SectionLabel, StatusDot } from "./primitives";
import { api } from "@/lib/api";
import type { Product, MerchantCatalog, MerchantPolicy } from "@/lib/types";

const accentText = {
  buyer: "text-buyer",
  merchant: "text-merchant",
  approved: "text-approved",
} as const;

export function MerchantCenter() {
  const [view, setView] = useState<"human" | "agent">("human");
  const [catalog, setCatalog] = useState<MerchantCatalog | null>(null);
  const [policy, setPolicy] = useState<MerchantPolicy | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [catalogData, policyData, productsData] = await Promise.all([
          api.getMerchantCatalog(1).catch(() => null),
          api.getMerchantPolicy(1).catch(() => null),
          // We'll use the products from catalog for the human view
        ]);

        if (catalogData) {
          setCatalog(catalogData);
          // Transform catalog products to Product type
          const transformedProducts: Product[] = catalogData.catalog.map((p) => ({
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

        if (policyData) {
          setPolicy(policyData);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to fetch merchant data");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const agentFeed = catalog
    ? {
        merchant: catalog.merchant,
        protocol: catalog.protocol,
        catalog: catalog.catalog.map((p) => ({
          sku: p.sku,
          title: p.title,
          category: p.category,
          currency: p.currency,
          base_price: p.base_price,
          stock: p.stock,
          delivery_sla_days: p.delivery_sla_days,
          pricing_tiers: p.pricing_tiers,
        })),
      }
    : null;

  // Mock stats - in production these would come from a stats endpoint
  // For now, compute from available data
  const stats = [
    {
      label: "Today's Agent Revenue",
      value: 0,
      prefix: "₹",
      accent: "merchant" as const,
    },
    {
      label: "Active Agent Requests",
      value: 0,
      prefix: "",
      accent: "buyer" as const,
    },
    {
      label: "Negotiation Success Rate",
      value: 0,
      prefix: "",
      suffix: "%",
      accent: "approved" as const,
    },
    {
      label: "Stock Units Reserved",
      value: products.reduce((sum, p) => sum + p.stock, 0),
      prefix: "",
      accent: "buyer" as const,
    },
  ];

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map((s, i) => (
          <FadeIn key={s.label} delay={i * 0.06}>
            <GlassPanel className="relative overflow-hidden p-5">
              <div
                className={cn(
                  "pointer-events-none absolute -right-10 -top-10 size-28 rounded-full blur-2xl opacity-25",
                  s.accent === "merchant"
                    ? "bg-merchant"
                    : s.accent === "approved"
                      ? "bg-approved"
                      : "bg-buyer",
                )}
              />
              <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{s.label}</p>
              <p className={cn("mt-3 text-3xl font-semibold", accentText[s.accent])}>
                <AnimatedCounter value={s.value} prefix={s.prefix} suffix={s.suffix ?? ""} />
              </p>
            </GlassPanel>
          </FadeIn>
        ))}
      </div>

      <FadeIn delay={0.1}>
        <GlassPanel className="p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <SectionLabel icon={<Gauge className="size-3.5" />} tone="merchant">
              Dual-Mode Catalog
            </SectionLabel>
            <div className="flex rounded-xl border border-border bg-foreground/5 p-1">
              {(
                [
                  { key: "human", label: "Human UI Table", icon: Table2 },
                  { key: "agent", label: "Agent-Readable JSON", icon: Braces },
                ] as const
              ).map((t) => (
                <button
                  key={t.key}
                  onClick={() => setView(t.key)}
                  className={cn(
                    "relative flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium transition",
                    view === t.key ? "text-merchant" : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {view === t.key ? (
                    <motion.span
                      layoutId="catalog-toggle"
                      className="absolute inset-0 rounded-lg border border-merchant/40 bg-merchant/10"
                    />
                  ) : null}
                  <t.icon className="relative size-3.5" />
                  <span className="relative">{t.label}</span>
                </button>
              ))}
            </div>
          </div>

          <motion.div key={view} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mt-4">
            {view === "human" ? (
              <div className="overflow-x-auto rounded-xl border border-border">
                {loading ? (
                  <div className="p-8 text-center text-muted-foreground">
                    <StatusDot tone="merchant" className="mx-auto" />
                    <p className="mt-2">Loading catalog…</p>
                  </div>
                ) : error ? (
                  <div className="p-8 text-center text-blocked">
                    <p>Failed to load catalog: {error}</p>
                  </div>
                ) : (
                  <table className="w-full text-left text-sm">
                    <thead className="bg-foreground/5 text-[11px] uppercase tracking-wider text-muted-foreground">
                      <tr>
                        <th className="px-4 py-3 font-medium">Product</th>
                        <th className="px-4 py-3 font-medium">Merchant</th>
                        <th className="px-4 py-3 font-medium">Stock</th>
                        <th className="px-4 py-3 font-medium">Base price</th>
                        <th className="px-4 py-3 font-medium">Bulk tiers</th>
                      </tr>
                    </thead>
                    <tbody>
                      {products.map((p) => (
                        <tr key={p.id} className="border-t border-border transition hover:bg-foreground/5">
                          <td className="px-4 py-3 font-medium">{p.name}</td>
                          <td className="px-4 py-3 text-muted-foreground">{p.merchant}</td>
                          <td className="px-4 py-3 font-mono">
                            <span className={p.stock < 100 ? "text-merchant" : "text-approved"}>{p.stock}</span>
                          </td>
                          <td className="px-4 py-3 font-mono">{inr(p.base_price)}</td>
                          <td className="px-4 py-3">
                            <div className="flex flex-wrap gap-1.5">
                              {p.pricing_tiers?.slice(1).map((t) => (
                                <Chip key={t.minQty} tone="merchant">
                                  {t.minQty}+ → {inr(t.unitPrice)}
                                </Chip>
                              ))}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            ) : (
              <div className="rounded-xl border border-border bg-background/70">
                {loading ? (
                  <div className="p-8 text-center text-muted-foreground">
                    <StatusDot tone="merchant" className="mx-auto" />
                    <p className="mt-2">Loading agent catalog…</p>
                  </div>
                ) : agentFeed ? (
                  <>
                    <div className="flex items-center gap-2 border-b border-border px-4 py-2.5 font-mono text-[11px] text-muted-foreground">
                      <Code2 className="size-3.5 text-merchant" />
                      GET /api/merchants/1/catalog · application/json
                    </div>
                    <pre className="max-h-96 overflow-auto p-4 font-mono text-[11px] leading-relaxed text-approved">
                      <code>{JSON.stringify(agentFeed, null, 2)}</code>
                    </pre>
                  </>
                ) : (
                  <div className="p-8 text-center text-blocked">
                    <p>Failed to load agent catalog</p>
                  </div>
                )}
              </div>
            )}
          </motion.div>
        </GlassPanel>
      </FadeIn>

      <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <FadeIn delay={0.15}>
          <GlassPanel className="h-full p-5">
            <div className="flex items-center justify-between">
              <SectionLabel icon={<Radio className="size-3.5" />} tone="merchant">
                Live Negotiation Terminal
              </SectionLabel>
              <div className="flex items-center gap-2 font-mono text-[11px] text-merchant">
                <StatusDot tone="merchant" /> LISTENING
              </div>
            </div>

            <div className="mt-4 space-y-3">
              {loading || !catalog ? (
                <div className="text-center text-muted-foreground py-8">
                  <StatusDot tone="merchant" />
                  <p className="mt-2">Waiting for catalog data…</p>
                </div>
              ) : (
                <>
                  <div className="rounded-xl border border-merchant/30 bg-merchant/5 p-4 font-mono text-xs">
                    <p className="text-merchant">POST /api/negotiate</p>
                    <p className="mt-1 text-muted-foreground">
                      Request bulk pricing for any product from the catalog above
                    </p>
                  </div>
                </>
              )}
            </div>
          </GlassPanel>
        </FadeIn>

        <FadeIn delay={0.2}>
          <GlassPanel className="h-full p-5">
            <SectionLabel icon={<ShieldAlert className="size-3.5" />} tone="blocked">
              Guardrails & Non-Negotiable Rules
            </SectionLabel>
            <div className="mt-4 space-y-3">
              {policy ? (
                <>
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="rounded-xl border border-border bg-foreground/5 p-4"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-medium">Negotiation Floor</p>
                      <span className="font-mono text-sm text-merchant">{(policy.negotiation_floor_pct * 100).toFixed(0)}%</span>
                    </div>
                    <p className="mt-1 text-[11px] text-muted-foreground">
                      Counter-offers never breach the floor margin per SKU.
                    </p>
                  </motion.div>
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.15 }}
                    className="rounded-xl border border-border bg-foreground/5 p-4"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-medium">Max Automated Order Value</p>
                      <span className="font-mono text-sm text-merchant">
                        {policy.agent_transaction_limit ? inr(policy.agent_transaction_limit) : "Unlimited"}
                      </span>
                    </div>
                    <p className="mt-1 text-[11px] text-muted-foreground">
                      Above this, a human merchant op must sign off.
                    </p>
                  </motion.div>
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="rounded-xl border border-border bg-foreground/5 p-4"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-medium">Allowed Categories</p>
                      <span className="font-mono text-sm text-merchant">{policy.allowed_categories.join(", ")}</span>
                    </div>
                    <p className="mt-1 text-[11px] text-muted-foreground">
                      Only these categories are permitted for agent transactions.
                    </p>
                  </motion.div>
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.25 }}
                    className="rounded-xl border border-border bg-foreground/5 p-4"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-medium">Negotiation Floor Guard</p>
                      <span className="font-mono text-sm text-merchant">Deterministic</span>
                    </div>
                    <p className="mt-1 text-[11px] text-muted-foreground">
                      Tier table lookup only — no LLM free-form pricing.
                    </p>
                  </motion.div>
                </>
              ) : (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="rounded-xl border border-border bg-foreground/5 p-4 text-center text-muted-foreground"
                >
                  <StatusDot tone="merchant" className="mx-auto" />
                  <p className="mt-2">Loading policy…</p>
                </motion.div>
              )}
            </div>
          </GlassPanel>
        </FadeIn>
      </div>
    </div>
  );
}