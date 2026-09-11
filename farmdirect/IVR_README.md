# 📞 FarmDirect Multilingual IVR

FarmDirect's IVR is a real alternate interface to the same marketplace backend. It does not use a separate fake database: listings, orders, payments, delivery state, earnings and AI/market-price services come from the same shared database and service modules used by the web app (SQLite locally, PostgreSQL when deployed with `DATABASE_URL`).

## Call languages
The simulator exposes **23 selectable languages**: English plus the 22 Scheduled Indian languages. Two-digit DTMF codes `01–23` are buffered before the backend receives the selection, avoiding collisions with main-menu actions.

Browser speech-to-text uses the selected language's BCP-47 locale when Web Speech is available. Text and keypad input remain available as deterministic fallbacks.

## Main menu

```text
1  Place New Order / Buy Produce
2  List Produce for Sale
3  Market Price
4  My Orders
5  Delivery Status
6  Bulk Order Opportunities
7  Earnings
8  Change Language
9  More Services
*  Help
```

### More Services

```text
1  AI Demand Forecast
2  My Active Listings / Stock
3  Payment & Settlement Status
4  My Farm Profile
5  AI Price Recommendation
6  Place New Order
8  Change Language
0  Main Menu
```

## Important behavior
- Purchase orders created by IVR use the same shared order engine as web checkout.
- Stock is reduced and payment/delivery rows are created normally.
- Listing quality grades are exactly `A`, `B`, `C` everywhere.
- If an entered price is challenged and the farmer supplies a corrected price, the corrected value becomes the source of truth before confirmation/database write.
- Market-price questions use the resilient mandi-price cache/provider chain when verified data is available and clearly distinguish official/cached/estimated values.
- Consumer and bulk-buyer callers can place orders; farmer-only services remain role-protected.

## Simulator
Open:

```text
/ivr/simulator
```

The simulator includes:
- caller identity selector
- 23-language call selector
- DTMF keypad
- microphone / live voice-to-text transcript
- typed-input fallback
- transcript bubbles
- current session state
- detected intent panel
- real backend-action result panel

## API

```text
POST /api/ivr/incoming
POST /api/ivr/input
GET  /api/ivr/session?session_token=
POST /api/ivr/callback
POST /api/ivr/hangup
GET  /api/ivr/mode
GET  /api/ivr/admin/stats
GET  /api/ivr/admin/calls
GET  /api/ivr/admin/call/<id>
```

## Production telephony
The included provider abstraction supports a mock/in-app simulator by default. Real telephony can be connected through `IVR_MODE=production` plus a supported provider adapter/credentials. The web simulator requires no telephony API key.

Typical optional environment variables:

```text
IVR_MODE=production
IVR_TELEPHONY_PROVIDER=twilio
IVR_TWILIO_ACCOUNT_SID=...
IVR_TWILIO_AUTH_TOKEN=...
IVR_TWILIO_NUMBER=...
IVR_PUBLIC_BASE_URL=https://...
```

External production STT/TTS/NLU providers are optional. The SIH simulator keeps local/Browser APIs and deterministic fallbacks so the demo does not depend on them.

## Demo caller numbers
Seeded callers are selectable directly in the simulator. Example farmer:

```text
Vikram Patil
+91 98201 10001
vikram@farmdirect.in / farm123
```

Use the Login page's one-tap demo accounts for web-role testing.
