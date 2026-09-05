export type Merchant = {
  id: string;
  name: string;
  rating: number;
};

export type PricingTier = { minQty: number; unitPrice: number };

export type Product = {
  id: string;
  name: string;
  merchantId: string;
  merchant: string;
  category: string;
  unitPrice: number;
  stock: number;
  deliveryDays: number;
  specs: string[];
  tiers: PricingTier[];
  score: number;
};

export const MERCHANTS: Merchant[] = [
  { id: "m_tech", name: "TechSupply Co.", rating: 4.8 },
  { id: "m_aura", name: "Aura Gear", rating: 4.5 },
];

export const PRODUCTS: Product[] = [
  {
    id: "p1",
    name: "Type-C Braided Cable 100W",
    merchantId: "m_tech",
    merchant: "TechSupply Co.",
    category: "Electronics",
    unitPrice: 320,
    stock: 480,
    deliveryDays: 2,
    specs: ["100W PD", "1.5m nylon braid", "480Mbps", "12-mo warranty"],
    tiers: [
      { minQty: 1, unitPrice: 320 },
      { minQty: 10, unitPrice: 300 },
      { minQty: 15, unitPrice: 290 },
      { minQty: 50, unitPrice: 275 },
    ],
    score: 94,
  },
  {
    id: "p2",
    name: "Type-C Fast Cable 60W",
    merchantId: "m_aura",
    merchant: "Aura Gear",
    category: "Electronics",
    unitPrice: 285,
    stock: 120,
    deliveryDays: 5,
    specs: ["60W PD", "1m TPE", "480Mbps", "6-mo warranty"],
    tiers: [
      { minQty: 1, unitPrice: 285 },
      { minQty: 20, unitPrice: 270 },
    ],
    score: 78,
  },
  {
    id: "p3",
    name: "Mechanical Keyboard TKL",
    merchantId: "m_tech",
    merchant: "TechSupply Co.",
    category: "Electronics",
    unitPrice: 4200,
    stock: 62,
    deliveryDays: 3,
    specs: ["Hot-swap", "Linear reds", "USB-C detach", "PBT caps"],
    tiers: [
      { minQty: 1, unitPrice: 4200 },
      { minQty: 10, unitPrice: 3950 },
    ],
    score: 71,
  },
  {
    id: "p4",
    name: "Ergonomic Desk Mat XL",
    merchantId: "m_aura",
    merchant: "Aura Gear",
    category: "Accessories",
    unitPrice: 899,
    stock: 240,
    deliveryDays: 4,
    specs: ["900x400mm", "Cork base", "Water resistant"],
    tiers: [
      { minQty: 1, unitPrice: 899 },
      { minQty: 25, unitPrice: 820 },
    ],
    score: 66,
  },
];

export type Scenario = "auto" | "threshold" | "webhook_fail";

export const SCENARIOS: Record<
  Scenario,
  { label: string; qty: number; unitPrice: number; productId: string }
> = {
  auto: { label: "Normal Auto-Approve Flow", qty: 9, unitPrice: 300, productId: "p1" },
  threshold: { label: "Over Threshold Flow", qty: 15, unitPrice: 290, productId: "p1" },
  webhook_fail: { label: "Payment Webhook Failure", qty: 15, unitPrice: 290, productId: "p1" },
};

export const CONSTRAINTS = { dailyLimit: 5000, autoApproveUnder: 3000, maxTxnCap: 4500 };

export const inr = (n: number) =>
  "₹" + n.toLocaleString("en-IN", { maximumFractionDigits: 2 });

export function getPricingTier(product: Product, qty: number): PricingTier {
  return (
    [...product.tiers].reverse().find((t) => qty >= t.minQty) ??
    product.tiers[0] ?? { minQty: 1, unitPrice: product.unitPrice }
  );
}

export const MERCHANT_STATS = [
  { label: "Today's Agent Revenue", value: 184250, prefix: "₹", accent: "merchant" as const },
  { label: "Active Agent Requests", value: 27, prefix: "", accent: "buyer" as const },
  { label: "Negotiation Success Rate", value: 86, prefix: "", suffix: "%", accent: "approved" as const },
  { label: "Stock Units Reserved", value: 1342, prefix: "", accent: "buyer" as const },
];

export const MERCHANT_GUARDRAILS = [
  { title: "Minimum Margin", value: "18%", detail: "Counter-offers never breach the floor margin per SKU." },
  { title: "Max Automated Order Value", value: "₹50,000", detail: "Above this, a human merchant op must sign off." },
  { title: "Category Restrictions", value: "3 blocked", detail: "Batteries, licensed software, gift cards." },
  { title: "Negotiation Floor Guard", value: "Deterministic", detail: "Tier table lookup only — no LLM free-form pricing." },
];

export type AuditActor = "SYSTEM" | "BUYER AGENT" | "MERCHANT AGENT" | "POLICY ENGINE" | "HUMAN";

export type AuditEvent = {
  id: string;
  actor: AuditActor;
  title: string;
  time: string;
  payload: Record<string, unknown>;
  tone?: "buyer" | "merchant" | "approved" | "blocked" | "neutral";
};
