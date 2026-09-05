import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { ConversationalCheckout } from "@/components/acg/conversational-checkout";
import { api } from "@/lib/api";
import { Loader2 } from "lucide-react";

export const Route = createFileRoute("/checkout/$purchaseIntentId")({
  component: CheckoutPage,
});

function CheckoutPage() {
  const { purchaseIntentId } = Route.useParams();
  const intentId = parseInt(purchaseIntentId, 10);

  const [purchaseIntent, setPurchaseIntent] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPurchaseIntent = async () => {
      try {
        setLoading(true);
        const response = await api.getPurchaseIntent(parseInt(purchaseIntentId, 10));
        setPurchaseIntent(response);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load purchase intent");
      } finally {
        setLoading(false);
      }
    };

    fetchPurchaseIntent();
  }, [purchaseIntentId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="size-8 animate-spin border-4 border-buyer border-t-transparent rounded-full" />
          <p className="text-muted-foreground">Loading checkout...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center p-8">
          <p className="text-blocked text-lg">Error: {error}</p>
          <a href="/" className="text-buyer hover:underline mt-4 inline-block">
            Back to Home
          </a>
        </div>
      </div>
    );
  }

  if (!purchaseIntent) {
    return null;
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-4xl mx-auto py-8 px-4">
        <ConversationalCheckout
          purchaseIntent={{
            id: purchaseIntent.id,
            amount: purchaseIntent.amount,
            unit_price: purchaseIntent.unit_price,
            quantity: purchaseIntent.quantity,
            status: purchaseIntent.status,
            product: purchaseIntent.product
              ? {
                  id: purchaseIntent.product.id,
                  name: purchaseIntent.product.name,
                  merchant: typeof purchaseIntent.product.merchant === 'string' 
                    ? purchaseIntent.product.merchant 
                    : purchaseIntent.product.merchant?.name || "",
                  category: purchaseIntent.product.category,
                }
              : { id: 0, name: "", merchant: "", category: "" },
            merchant: purchaseIntent.merchant
              ? { id: purchaseIntent.merchant.id, name: purchaseIntent.merchant.name }
              : { id: 0, name: "" },
            razorpay_order_id: purchaseIntent.razorpay_order_id || "",
            razorpay_key_id: import.meta.env.VITE_RAZORPAY_KEY_ID ?? "rzp_test_demo",
          }}
          onClose={() => window.history.back()}
          onSuccess={() => (window.location.href = "/")}
        />
      </div>
    </div>
  );
}