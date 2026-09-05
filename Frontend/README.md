# Agent Commerce Hub

Create a ultra-modern, high-tech dark mode frontend dashboard for "Agent Commerce Gateway" — an AI-native agentic shopping and deterministic transaction platform built for the Razorpay Buildathon 2026. 

Design Aesthetics:

- Visual Theme: Cyberpunk-meets-fintech minimalism. Deep obsidian/slate background (`#0B0F17`), sleek glassmorphism panels (backdrop blur, subtle border highlights), glowing neon accents (Cyan `#00F0FF` for Buyer Agent, Amber/Gold `#FFB800` for Merchant Agent, Emerald `#00FF9D` for Policy Approved, and Crimson `#FF3B3B` for Guardrail/Blocked).

- Typography: Sharp, ultra-scannable sans-serif (e.g., Inter / JetBrains Mono for code & transaction amounts).

- Animations: Smooth Framer Motion page transitions, pulsing agent state indicators, glowing audit node lines, micro-interactions on button hovers, and animated status badges.

The UI is split into two primary view modes toggleable from the top navigation:

1. 🛒 Buyer Agent Studio

2. 🏬 Merchant Command Center

---

### PAGE 1: BUYER AGENT STUDIO

1. Top Header Bar:

   - System Title: "AGENT COMMERCE GATEWAY" with an active system health green dot.

   - User Profile Badge with active spending constraints chip: "Daily Limit: ₹5,000 | Auto-Approve < ₹3,000".

   - View Switcher Tabs: [Buyer Studio] | [Merchant Center].

2. Natural Language Intent & Constraint Input Section:

   - A prominent central search/intent bar with floating particle glow effects.

   - Placeholder text: "e.g., Buy 15 high-speed Type-C mechanical cables under ₹4,500 total..."

   - Action Button: "Run Buyer Agent" (with animated shimmering icon).

   - Once submitted, trigger an animated "Intent Parser" popover card that breaks down the prompt into structured tag chips: `[Category: Electronics]` `[Max Budget: ₹4,500]` `[Qty: 15]` `[Delivery: < 3 days]`.

3. Agent Reasoning & Live Execution Canvas:

   - Left Panel — "Agent Thinking Stream": An animated live terminal view showing the Buyer Agent tool calls with typing effect and pulsing status indicators:

     - 🔍 `search_catalog(category="Electronics", max_price=300)` -> Found 6 candidates across 2 merchants.

     - 📊 `compare_products(ids=[p1, p2, p3])` -> Scoring matrix calculated.

     - 🤝 `request_negotiation(qty=15, merchant="TechSupply Co.")` -> Triggering Merchant Agent.

   - Right Panel — "Product Comparison & Selection":

     - Dynamic side-by-side product cards highlighting unit prices, specs, stock levels, and delivery SLAs.

     - The selected winning product gets a glowing neon cyan border and a structured "Why Picked" reasoning card with checkmarks.

4. Deterministic Policy Gate & Transaction Action (The Hero Section):

   - A high-impact "Policy Validation Engine" card showing real-time policy evaluation:

     - Rule 1: Allow-List Category -> ✅ PASSED

     - Rule 2: Max Transaction Cap -> ✅ PASSED

     - Rule 3: Daily Spend Limit -> ✅ PASSED

     - Rule 4: Autonomous Threshold Check -> ⚠️ REQUIRES HUMAN APPROVAL (if amount > ₹3,000) or ✅ AUTO-ALLOWED (if ≤ ₹3,000).

   - Interactive Approval / Payment Drawer:

     - If NEEDS_APPROVAL: Display an interactive `ApprovalRequestCard` with a pulsing amber light and two buttons: [Approve Purchase] and [Reject Proposal].

     - Clicking "Approve" triggers a crisp sound/haptic animation, transitioning the state to "APPROVED".

     - Action Bar: Glowing "Pay via Razorpay" button. Clicking this triggers a simulated Razorpay modal overlay (showing Order ID, Amount, and simulated test UPI / Card checkout).

5. Real-Time Transaction Audit Trail Timeline (Bottom Section):

   - Vertical timeline view with expandable event cards.

   - Each event features an actor badge (`[SYSTEM]`, `[BUYER AGENT]`, `[MERCHANT AGENT]`, `[POLICY ENGINE]`, `[HUMAN]`), exact timestamp, event title, and expandable raw JSON payload view.

---

### PAGE 2: MERCHANT COMMAND CENTER

1. Top Stat Bar:

   - Glassmorphic cards with animated counters: "Today's Agent Revenue", "Active Agent Requests", "Negotiation Success Rate", "Stock Units Reserved".

2. Dual-Mode Catalog View:

   - Toggle Switch: [Human UI Table] vs [Agent-Readable JSON].

   - Human View: Clean data table displaying products, stock counts, base pricing, and active bulk discount tier tags.

   - Agent View: Code block with syntax highlighting showing the exact structured JSON feed exposed to external AI buyer agents.

3. Live Merchant Agent & Negotiation Terminal:

   - Real-time feed of inbound buyer agent proposals.

   - Visual breakdown of the deterministic negotiation lookup:

     - "Inbound offer: ₹280/unit for 15 units" -> `get_pricing_tier(15)` -> "Tier Match: ₹290/unit" -> "Negotiation Floor Guard: ✅ SAFE" -> Counter Offer Sent: ₹290.

4. Guardrails & Policy Rules Display:

   - Cards showing non-negotiable merchant rules: Minimum Margin %, Max Automated Order Value, Category Restrictions.

---

### INTERACTION & MOCK DATA

- Seed mock data for 2 Merchants: "TechSupply Co." and "Aura Gear".

- Pre-load sample products (Mechanical Keyboards, Type-C Braided Cables, Ergonomic Desk Mats) with bulk pricing tiers.

- Include interactive toggle controls in a floating dev toolbar at the bottom right:

  - [Simulate: Normal Auto-Approve Flow (< ₹3,000)]

  - [Simulate: Over Threshold Flow (> ₹3,000 - Trigger Case 4)]

  - [Simulate: Payment Webhook Failure]

- Use Lucide icons, Framer Motion animations for list items entering the DOM, Tailwind CSS glassmorphism classes (`backdrop-blur-md`, `bg-white/5`, `border-white/10`), and smooth tab transitions.

This project was built with [Lovable](https://lovable.dev).

**Live app**: https://neo-agent-trade.lovable.app

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/ef9f8a92-9a40-4b53-a769-efa07d28d634).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
