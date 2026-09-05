const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const DEMO_TOKEN = import.meta.env.VITE_DEMO_TOKEN ?? "demo-token";

interface RequestOptions extends RequestInit {
  params?: Record<string, string>;
}

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  endpoint: string,
  options: RequestOptions = {},
): Promise<T> {
  const { params, headers, ...fetchOptions } = options;

  const url = new URL(`${API_BASE_URL}${endpoint}`);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      url.searchParams.append(key, value);
    });
  }

  const response = await fetch(url.toString(), {
    ...fetchOptions,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${DEMO_TOKEN}`,
      ...headers,
    },
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(
      data.detail ?? `Request failed with status ${response.status}`,
      response.status,
      data,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

export const api = {
  // Buyer endpoints
  createIntent: (text: string) =>
    request<{ success: boolean; purchase_intent_id: number; status: string; error?: string; razorpay_order_id?: string }>(
      "/api/intent",
      { method: "POST", body: JSON.stringify({ text }) },
    ),

  getPurchaseIntent: (id: number) =>
    request<{
      id: number;
      user_id: number;
      product_id: number;
      merchant_id: number;
      quantity: number;
      unit_price: number;
      amount: number;
      status: string;
      reasoning: string;
      policy_reason: string;
      created_at: string;
    }>(`/api/purchase-intents/${id}`),

  approvePurchaseIntent: (id: number) =>
    request<{ success: boolean; purchase_intent_id: number; status: string; error?: string; razorpay_order_id?: string }>(
      `/api/purchase-intents/${id}/approve`,
      { method: "POST", body: JSON.stringify({ approve: true }) },
    ),

  rejectPurchaseIntent: (id: number) =>
    request<{ success: boolean; purchase_intent_id: number; status: string; error?: string }>(
      `/api/purchase-intents/${id}/reject`,
      { method: "POST" },
    ),

  // Payment endpoints
  createRazorpayOrder: (purchaseIntentId: number) =>
    request<{
      success: boolean;
      razorpay_order_id: string;
      amount: number;
      currency: string;
      key_id: string;
    }>(`/api/payments/purchase-intents/${purchaseIntentId}/pay/create-order`, {
      method: "POST",
    }),

  verifyPayment: (data: {
    razorpay_order_id: string;
    razorpay_payment_id: string;
    razorpay_signature: string;
  }) =>
    request<{ success: boolean }>("/api/payments/verify", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Negotiation endpoints
  negotiate: (data: { product_id: number; quantity: number; offered_price?: number }) =>
    request<{
      success: boolean;
      unit_price: number;
      quantity: number;
      countered: boolean;
      message?: string;
    }>("/api/negotiate", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  createNegotiation: (data: {
    purchase_intent_id: number;
    requested_qty: number;
    offered_price: number;
  }) =>
    request<{
      success: boolean;
      negotiation_id: number;
      unit_price: number;
      countered: boolean;
    }>("/api/negotiations", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getNegotiation: (id: number) =>
    request<{
      id: number;
      purchase_intent_id: number;
      requested_qty: number;
      offered_price: number;
      countered_price: number;
      accepted: boolean | null;
      merchant_reasoning: string | null;
    }>(`/api/negotiations/${id}`),

  // Merchant endpoints
  getMerchantCatalog: (merchantId: number) =>
    request<{
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
        pricing_tiers: Array<{ minQty: number; unitPrice: number }>;
      }>;
    }>(`/api/merchants/${merchantId}/catalog`),

  getMerchantPolicy: (merchantId: number) =>
    request<{
      negotiation_floor_pct: number;
      agent_transaction_limit: number | null;
      allowed_categories: string[];
    }>(`/api/merchants/${merchantId}/policy`),

  // Audit endpoint
  getAuditTrail: (purchaseIntentId: number) =>
    request<Array<{
      id: number;
      purchase_intent_id: number | null;
      actor: string;
      event: string;
      payload: Record<string, unknown>;
      created_at: string;
    }>>(`/api/audit/${purchaseIntentId}`),

  // Health check
  health: () => request<{ status: string; service: string }>("/health"),

  // AI Chat endpoint
  chatWithAgent: (data: {
    question: string;
    productId?: number;
    productName?: string;
    merchantName?: string;
    category?: string;
    specs?: Record<string, any>;
    comparisonProducts?: Array<{ name: string; price: number; merchant: string; specs: Record<string, any> }>;
  }) =>
    request<{
      answer: string;
      type?: "text" | "product" | "comparison";
      metadata?: Record<string, any>;
    }>("/api/chat/agent", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Recommendations endpoint
  getRecommendations: (category: string, excludeIntentId: number) =>
    request<{
      products: Array<{
        id: number;
        name: string;
        merchant: string;
        price: number;
        category: string;
        specs: Record<string, any>;
      }>;
    }>(`/api/recommendations?category=${encodeURIComponent(category)}&exclude=${excludeIntentId}`),
};

export { ApiError };
export type { RequestOptions };