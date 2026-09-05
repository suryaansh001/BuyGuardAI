export type PurchaseIntentStatus =
  | "DRAFT"
  | "POLICY_CHECKED"
  | "ALLOWED"
  | "BLOCKED"
  | "NEEDS_APPROVAL"
  | "APPROVED"
  | "REJECTED"
  | "PAID"
  | "FAILED";

export interface PurchaseIntent {
  id: number;
  user_id: number;
  product_id: number;
  merchant_id: number;
  quantity: number;
  unit_price: number;
  amount: number;
  status: PurchaseIntentStatus;
  reasoning: string | null;
  policy_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface Product {
  id: number;
  name: string;
  category: string;
  description: string | null;
  merchant_id: number;
  base_price: number;
  currency: string;
  delivery_days: number;
  stock: number;
  spec: Record<string, unknown>;
  merchant: {
    id: number;
    name: string;
  };
  pricing_tiers?: Record<string, number>;
}

export interface ComparisonProduct {
  product_id: number;
  name: string;
  category: string;
  merchant: string;
  merchant_id: number;
  base_price: number;
  currency: string;
  delivery_days: number;
  stock: number;
  spec: Record<string, unknown>;
  pricing_tiers: Record<string, number>;
}

export interface Negotiation {
  id: number;
  purchase_intent_id: number;
  requested_qty: number;
  offered_price: number;
  countered_price: number | null;
  accepted: boolean | null;
  merchant_reasoning: string | null;
}

export interface AuditLogEntry {
  id: number;
  purchase_intent_id: number | null;
  actor: string;
  event: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface MerchantCatalog {
  merchant: string;
  protocol: string;
  catalog: Array<{
    sku: string;
    title: string;
    category: string;
    currency: string;
    base_price: number;
    stock: number;
    delivery_sla_days: number;
    pricing_tiers: Record<string, number>;
  }>;
}

export interface MerchantPolicy {
  negotiation_floor_pct: number;
  agent_transaction_limit: number | null;
  allowed_categories: string[];
}

export interface RazorpayOrderResponse {
  success: boolean;
  razorpay_order_id: string;
  amount: number;
  currency: string;
  key_id: string;
  error?: string;
}

export interface ApiError {
  detail: string;
}