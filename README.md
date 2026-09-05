# Agent Commerce Gateway (ACG)

**Deterministic Agentic Commerce Control Room** — Built for Razorpay Buildathon 2026, Track 01: AI Growth & Agentic Commerce.

> "Every money action explainable, bounded and gated. Show the audit trail and one failure handled gracefully."

---

## 🎯 Problem

Agent-to-agent commerce is the open problem of 2026 (NPCI UAP, ACP, AP2, x402). Merchants on Razorpay can't yet be **agent-readable** or **agent-transactable**.

**ACG solves this:**
- **Agent-readable catalog** — structured product data with pricing tiers, specs, stock
- **Conversational checkout** — buyer speaks naturally ("mechanical keyboard under ₹5000 within 3 days"), agent handles search/selection/policy/checkout
- **Deterministic guardrails** — policy engine evaluates *every* transaction against hard rules (max amount, daily cap, allow-list, approval threshold) — **no LLM decides money moves**
- **Full audit trail** — immutable log of every actor (buyer_agent, policy_engine, human, system) with payloads
- **Graceful failure handling** — payment failure → stock released, funds refunded, audit logged

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      BUYER STUDIO (React)                       │
│  Natural Language Intent  →  SSE Thinking Stream  →  Policy UI  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST + SSE
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND (Python)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ Intent      │  │ Buyer Agent │  │ Orchestrator│              │
│  │ Parser      │──│ (Tools)     │──│ + Policy    │              │
│  └─────────────┘  └─────────────┘  │   Engine    │              │
│                                    └──────┬──────┘              │
│                                           │                     │
│                    ┌──────────────────────┼──────────────┐      │
│                    ▼                      ▼              ▼      │
│             ┌───────────┐          ┌───────────┐    ┌─────────┐ │
│             │  Razorpay │          │  Audit    │    │  DB     │ │
│             │  (Test)   │          │  Logger   │    │ (Postgres)│
│             └───────────┘          └───────────┘    └─────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Core Principle: **LLMs Consult, Policy Engine Decides**

| Layer | Responsibility | Deterministic? |
|-------|---------------|----------------|
| **Intent Parser** | NL → structured constraints | ✅ (regex fallback) |
| **Buyer Agent** | Search, compare, reason, propose | ❌ (LLM) |
| **Policy Engine** | Allow / Approve / Block | ✅ (pure Python) |
| **Merchant Agent** | Pricing tiers, negotiation floor | ✅ (pure Python) |
| **Razorpay** | Settlement | ✅ (external) |
| **Audit Log** | Immutable trail | ✅ (append-only) |

---

## 📁 Project Structure

```
razorplay/
├── fastapi_backned/                 # Python FastAPI Backend
│   ├── app/
│   │   ├── agents/                  # Agent implementations
│   │   │   ├── buyer_agent.py       # Buyer agent (Groq + Ollama)
│   │   │   ├── merchant_agent.py    # Merchant agent (negotiation)
│   │   │   ├── orchestrator.py      # Purchase flow orchestration
│   │   │   ├── intent_parser.py     # NL → constraints (Groq + fallback)
│   │   │   ├── ollama_client.py     # Local LLM client + tool calling
│   │   │   └── tools.py             # 7 tools across 2 personas
│   │   ├── api/                     # REST + SSE endpoints
│   │   │   ├── routes_buyer.py      # /api/intent, /stream, /chat
│   │   │   ├── routes_merchant.py   # Merchant endpoints
│   │   │   ├── routes_campaign.py   # Campaign management
│   │   │   ├── routes_audit.py      # Audit trail
│   │   │   └── routes_payments.py   # Razorpay webhooks
│   │   ├── policy/                  # Deterministic policy engine
│   │   │   ├── engine.py            # evaluate() — pure Python
│   │   │   └── models.py            # PolicyResult, BuyerPolicy
│   │   ├── audit/                   # Audit logging
│   │   ├── catalog/                 # Product search/compare
│   │   ├── razorpay_service/        # Razorpay integration
│   │   ├── db/                      # SQLAlchemy models + session
│   │   └── core/config.py           # Settings (env-based)
│   ├── tests/                       # Pytest suite
│   └── seed.py                      # Demo data seeding
│
├── neo-agent-trade/                 # React Frontend (TanStack Router + Vite)
│   ├── src/
│   │   ├── components/acg/          # ACG-specific components
│   │   │   ├── buyer-studio.tsx     # Main buyer interface
│   │   │   ├── merchant-center.tsx  # Merchant dashboard
│   │   │   ├── negotiation-center.tsx
│   │   │   ├── audit-timeline.tsx   # Expandable audit log
│   │   │   └── primitives/          # Chips, StatusDot, GlassPanel
│   │   ├── routes/                  # File-based routing
│   │   │   ├── index.tsx            # Dashboard (3 tabs)
│   │   │   └── checkout.$id.tsx     # Conversational checkout
│   │   ├── lib/                     # API client, types, utils
│   │   └── styles.css               # Tailwind + custom CSS vars
│   └── package.json
│
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node 20+
- PostgreSQL 15+
- (Optional) Ollama running locally: `ollama pull llama3.2:latest`
- (Optional) Groq API key for cloud LLM

### Backend Setup

```bash
cd fastapi_backned

# Create virtual env
python -m venv .venv && source .venv/bin/activate

# Install deps
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your DATABASE_URL, RAZORPAY keys, GROQ_API_KEY

# Run migrations (Alembic) or create tables
python -c "from app.db.session import init_db; import asyncio; asyncio.run(init_db())"

# Seed demo data
python seed.py

# Start server
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd neo-agent-trade

# Install deps
npm install  # or bun install

# Configure API URL
echo "VITE_API_URL=http://localhost:8000" > .env

# Start dev server
npm run dev  # or bun dev
```

Open `http://localhost:5173` → **Buyer Studio** tab.

---

## 🎮 Demo Flows (Dev Toolbar)

Click **Dev Toolbar** (bottom-right) for one-click demos:

| Button | Intent | Expected Flow |
|--------|--------|---------------|
| **Auto-Approve Flow** | `usb hub under ₹2000` | Parsed → Search → Propose → Policy ALLOWED → Razorpay order |
| **Over Threshold Flow** | `mechanical keyboard under ₹5000` | Parsed → Search → Propose → Policy NEEDS_APPROVAL → Human Approve → Razorpay |
| **Blocked Flow** | `4k monitor under ₹40000` | Parsed → Search → Propose → Policy BLOCKED (exceeds max txn) |
| **Payment Failure Test** | `mechanical keyboard under ₹5000` + approve → use `failure@razorpay` UPI | Webhook fails → Stock released → Audit logged |

---

## 🔧 Key API Endpoints

### Buyer Flow
```
POST   /api/intent              # Create intent (sync)
POST   /api/intent/stream       # Create intent (SSE thinking stream)
GET    /api/purchase-intents/:id
POST   /api/purchase-intents/:id/approve
POST   /api/purchase-intents/:id/reject
POST   /api/chat/agent          # Conversational Q&A about products
GET    /api/recommendations     # Similar products by category
```

### Merchant / Campaigns
```
POST   /api/merchants
GET    /api/merchants/:id
POST   /api/campaigns
GET    /api/campaigns
POST   /api/campaigns/:id/activate
```

### Audit
```
GET    /api/audit/:intent_id    # Full audit trail
```

---

## 🧠 Multi-Model Fallback Chain

```
User Intent
    │
    ▼
┌─────────────────────┐
│  Groq (Primary)     │  llama-3.3-70b-versatile
│  - Intent parsing   │  - Fast, cloud
│  - Buyer agent      │  - Structured output
└─────────┬───────────┘
          │ fails (rate limit, network, key missing)
          ▼
┌─────────────────────┐
│  Ollama (Local)     │  llama3.2:latest
│  - Full tool loop   │  - Runs offline
│  - Same tools       │  - Tool calling support
└─────────┬───────────┘
          │ fails (Ollama down, model error)
          ▼
┌─────────────────────┐
│  Deterministic      │  Zero LLM
│  Fallback           │  - Regex parse intent
│  (fallback_buyer_   │  - Search → Compare →
│   agent)            │    Propose (cheapest match)
└─────────────────────┘
```

Configured in `app/agents/buyer_agent.py:121-129` — tries Groq → Ollama → Deterministic.

---

## 🛡 Policy Engine Rules (Deterministic)

`app/policy/engine.py:evaluate()` — **no LLM involved**:

```python
def evaluate(category, amount, merchant_id, spent_today, policy):
    1. Category in blocked_categories?           → BLOCKED
    2. Category not in allowed_categories?       → BLOCKED
    3. Merchant not in allowed_merchant_ids?     → BLOCKED
    4. Amount > max_transaction_amount?          → BLOCKED
    5. Spent_today + amount > daily_spending_limit? → BLOCKED
    6. Amount > approval_required_above?         → NEEDS_APPROVAL
    7. Otherwise                                 → ALLOWED
```

Each user has a `buyer_policy` row — fully configurable per customer.

---

## 📋 Audit Trail Schema

Every state change logs to `audit_logs`:

```sql
actor          | event                    | payload
---------------|--------------------------|-----------------------------------
buyer_agent    | product_selected         | {product_id, reasoning}
system         | intent_received          | {raw_text}
policy_engine  | policy_evaluated         | {rule: "ALLOWED", reason: "..."}
human          | approval_requested       | {threshold, amount}
human          | approval_resolved        | {decision: "APPROVED"}
system         | razorpay_order_created   | {order_id, amount}
system         | payment_captured         | {payment_id}
system         | payment_failed           | {error, refunded: true}
```

Frontend: **Audit Timeline** panel (expandable, color-coded by actor).

---

## 🧪 Testing

```bash
cd fastapi_backned

# Run all tests
pytest -v

# Specific test files
pytest tests/test_intent_parser.py -v
pytest tests/test_policy_engine.py -v
pytest tests/test_orchestrator.py -v
pytest tests/test_buyer_agent.py -v
```

---

## 🔐 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `RAZORPAY_KEY_ID` | ⚠️ | Test key (or use mock mode) |
| `RAZORPAY_KEY_SECRET` | ⚠️ | Test secret |
| `GROQ_API_KEY` | ⚠️ | For cloud LLM (optional) |
| `OLLAMA_BASE_URL` | ⚠️ | Default `http://localhost:11434` |
| `SECRET_KEY` | ✅ | JWT signing |

Mock mode activates automatically if Razorpay keys are placeholder (`rzp_test_xxxxx`).

---

## 📦 Seed Data

`seed.py` creates:
- **2 Merchants**: TechCorp Electronics, OfficeSupplies Co.
- **6 Products**: Keyboards, monitors, USB hubs, notebooks, pens, novels
- **Pricing tiers** for bulk negotiation
- **1 User** with buyer policy:
  - Max transaction: ₹10,000
  - Daily limit: ₹25,000
  - Approval required above: ₹3,000
  - Allowed: Electronics, Office supplies, Books



## 🤝 Contributing

This is a hackathon submission. Issues/PRs welcome for:
- Additional agent tools
- More policy rule types
- Better Ollama model prompts
- Frontend polish

---

## 📄 License

MIT — Built for Razorpay Buildathon 2026.

---

## 🙏 Credits

- **Razorpay** — Test-mode APIs, webhook simulation
- **Groq** — Fast LLM inference
- **Ollama** — Local LLM runtime
- **FastAPI + SQLAlchemy + Pydantic** — Backend stack
- **TanStack Router + React + Tailwind + Motion** — Frontend stack