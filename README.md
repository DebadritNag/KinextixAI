# Kinetix AI — Intelligent Supply Chain Optimization System

A full-stack AI-powered logistics control tower that predicts disruptions, optimizes multi-objective routing, and explains decisions in natural language. Built with a **Python FastAPI** backend and a **Flutter Web** frontend.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [API Reference](#api-reference)
- [ML Services](#ml-services)
- [Frontend Pages](#frontend-pages)
- [Design System](#design-system)
- [Configuration](#configuration)
- [Testing](#testing)
- [Development Notes](#development-notes)

---

## Overview

Kinetix AI simulates a real-time supply chain control tower. A background simulation loop continuously generates and updates 50–100 mock shipments, feeds them through ML pipelines, and exposes the results via a REST API. The Flutter frontend polls the API every 5 seconds and renders an interactive dashboard with live OpenStreetMap tiles, risk alerts, route optimization sliders, and analytics charts.

Everything runs **entirely locally** — no cloud infrastructure required. The Hugging Face Router API is used for natural language explanations (powered by **Google Gemma 4B**) and falls back gracefully to template-based responses when unavailable.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Flutter Web Frontend                        │
│  Landing → Login → Dashboard → Shipment Detail → Analytics     │
│  Settings → Profile → Solutions → Global Network               │
│  Riverpod StateNotifier providers │ go_router │ dio HTTP client │
└──────────────────────┬──────────────────────────────────────────┘
                       │ REST/JSON  http://localhost:8000
┌──────────────────────▼──────────────────────────────────────────┐
│                     FastAPI Backend                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │Disruption│  │   ETA    │  │Optim.    │  │  Reasoning    │  │
│  │Detector  │  │Predictor │  │Engine    │  │  Engine       │  │
│  │(IsoForest│  │(XGBoost) │  │(NetworkX)│  │(gemma-4-31B)  │  │
│  └──────────┘  └──────────┘  └──────────┘  └───────────────┘  │
│                   In-Memory Data Store                          │
│                   Simulation Loop (asyncio, 10–20s interval)    │
└─────────────────────────────────────────────────────────────────┘
                       │ Tile requests (CORS-safe)
┌──────────────────────▼──────────────────────────────────────────┐
│              CartoCDN / OpenStreetMap Tile Servers              │
│  https://{s}.basemaps.cartocdn.com/{style}/{z}/{x}/{y}.png      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Features

### Backend

- **Disruption Detection** — Isolation Forest anomaly detection on shipment features (location deviation, time deviation, weather severity, historical delay frequency). Classifies anomalies as LOW / MEDIUM / HIGH severity.
- **ETA Prediction** — XGBoost regression with 18 features including cyclical time encoding, one-hot weather, and haversine distance. Returns predicted arrival with ±1σ confidence interval.
- **Route Optimization** — NetworkX directed graph with 22 nodes (ports, warehouses, distribution centers, customs) and 58 edges. Min-max normalizes cost/time/carbon/risk before applying user-configurable weights. Returns top 3 routes labeled cheapest / fastest / greenest / safest.
- **Decision Explanation** — Calls the **Hugging Face Router API** (`router.huggingface.co/v1/chat/completions`) with model `google/gemma-4-31B-it`. 20-second timeout. Falls back to a deterministic template. Enforces 200-word maximum. Response includes `source: "model" | "fallback"`.
- **Simulation Loop** — Async background task generating 50–100 shipments, advancing positions, injecting random events (weather 5%, delay 5%, route deviation 2%, recovery 3%), and running ML pipelines every 10–20 seconds.
- **Demo Mode** — `POST /api/demo/trigger-disruption` forces a HIGH-severity alert on any shipment for live demonstrations.

### Frontend

- **Live Map** — `flutter_map` with CartoCDN tile layer (CORS-safe on Flutter Web), animated shipment markers, arc polylines (solid completed / dashed remaining), tap-to-inspect tooltips, and zoom controls wired to a shared `MapController`.
- **Risk Alerts Panel** — Color-coded alerts sorted by severity (HIGH → MEDIUM → LOW), auto-refreshing every 5 seconds via `StateNotifier` background polling (no loading flash on refresh).
- **Route Optimization Cards** — Top 3 routes with cost, ETA, carbon, and risk metrics. Recommended route highlighted.
- **Weight Sliders** — Four sliders (cost / time / carbon / risk) that trigger route recalculation.
- **Analytics Charts** — Delay trends (line), cost savings (bar), carbon reduction (line), and SLA compliance (circular gauge) using `fl_chart` with dynamic `maxY` scaling and label-interval throttling to prevent overlap.
- **Shipment Detail** — Bento grid with risk probability gauge, arrival variance forecast chart, AI Reasoning Engine card, shipment lifecycle timeline, live asset feed, and action buttons (Generate Report, Manage Risk).
- **Settings** — Redesigned bento grid layout: SLA thresholds (4 fields), risk sensitivity card, conflict alert card, penalty amounts with USD prefix inputs, and weight bias sliders.
- **Profile** — Edit profile bottom sheet, share action, security settings (2FA toggle, session management), preferences (theme mode, notifications, refresh rate).
- **Dark / Light Mode** — Full glassmorphism design system. Theme persists across sessions.
- **Performance** — `RepaintBoundary` around map and right panels. `StateNotifier` polling updates shipment list in-place (no `AsyncValue.loading` flash on background refresh). `ref.watch(provider.select(...))` for granular rebuilds.

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend framework | FastAPI + Uvicorn | 0.115.0 / 0.30.6 |
| Data validation | Pydantic v2 | 2.9.2 |
| ML — anomaly detection | scikit-learn IsolationForest | 1.5.2 |
| ML — ETA prediction | XGBoost | 2.1.1 |
| Graph optimization | NetworkX | 3.3 |
| NL explanation | HF Router API — `google/gemma-4-31B-it` | huggingface_hub 0.25.1 |
| HTTP client (backend) | httpx | 0.27.2 |
| Frontend framework | Flutter Web (Dart) | 3.x |
| State management | flutter_riverpod | 2.6.1 |
| Routing | go_router | 14.8.1 |
| HTTP client (frontend) | dio | 5.7.0 |
| Map tiles | flutter_map + CartoCDN | 8.3.0 |
| Charts | fl_chart | 0.70.2 |
| Typography | google_fonts (Plus Jakarta Sans, Fira Sans, Fira Code) | 6.2.1 |
| Backend tests | pytest + pytest-asyncio | — |
| Frontend tests | flutter_test | — |

---

## Project Structure

```
Kinetix/
├── .gitignore                    # Python, Flutter, IDE, OS ignores
├── README.md
├── backend/
│   ├── .env                      # HF_API_TOKEN (not committed)
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py               # FastAPI app, CORS, lifespan
│   │   ├── api/                  # FastAPI routers
│   │   │   ├── alerts.py
│   │   │   ├── analytics.py
│   │   │   ├── auth.py           # Mock auth (any credentials)
│   │   │   ├── demo.py
│   │   │   ├── explain.py
│   │   │   ├── optimize.py
│   │   │   ├── settings.py
│   │   │   └── shipments.py
│   │   ├── models/               # Pydantic data models
│   │   │   ├── alert.py
│   │   │   ├── analytics.py
│   │   │   ├── api.py
│   │   │   ├── optimization.py
│   │   │   ├── prediction.py
│   │   │   ├── settings.py
│   │   │   └── shipment.py
│   │   └── services/             # Business logic & ML
│   │       ├── data_store.py     # Thread-safe in-memory store
│   │       ├── disruption_detector.py  # IsolationForest
│   │       ├── eta_predictor.py        # XGBoost
│   │       ├── optimization_engine.py  # NetworkX graph
│   │       ├── reasoning_engine.py     # Gemma 4B via HF Router
│   │       └── simulation.py           # Async background loop
│   ├── models/
│   │   ├── .gitkeep
│   │   └── eta_model.json        # Persisted XGBoost model
│   └── tests/                    # pytest test suite
│       ├── test_api.py
│       ├── test_data_store.py
│       ├── test_disruption_detector.py
│       ├── test_eta_predictor.py
│       ├── test_optimization_engine.py
│       ├── test_reasoning_engine.py
│       └── test_simulation.py
└── frontend/
    ├── pubspec.yaml
    ├── web/
    │   ├── index.html            # CSP headers for CanvasKit + CartoCDN
    │   └── hero.png              # Landing page hero image (web-served copy)
    ├── assets/
    │   └── images/
    │       └── hero.png          # Flutter asset (registered in pubspec.yaml)
    └── lib/
        ├── main.dart
        ├── models/               # Dart data models (fromJson/toJson)
        │   ├── alert.dart
        │   ├── analytics.dart
        │   ├── optimization.dart
        │   ├── prediction.dart
        │   ├── settings.dart
        │   └── shipment.dart
        ├── pages/
        │   ├── landing_page.dart       # Hero + features + CTA
        │   ├── login_page.dart
        │   ├── dashboard_page.dart     # Map + panels + zoom controls
        │   ├── shipment_detail_page.dart  # Bento grid detail view
        │   ├── analytics_page.dart     # fl_chart charts
        │   ├── settings_page.dart      # Bento grid settings
        │   ├── profile_page.dart       # Edit profile + preferences
        │   ├── global_network_page.dart
        │   ├── solutions_page.dart
        │   └── book_demo_page.dart
        ├── providers/
        │   ├── auth_provider.dart
        │   ├── shipments_provider.dart  # StateNotifier (no loading flash)
        │   ├── alerts_provider.dart
        │   ├── analytics_provider.dart
        │   ├── routes_provider.dart
        │   ├── explain_provider.dart
        │   ├── settings_provider.dart
        │   ├── theme_provider.dart
        │   └── weights_provider.dart
        ├── router/
        │   └── app_router.dart         # go_router + auth guard
        ├── services/
        │   └── api_client.dart         # dio singleton + envelope interceptor
        ├── theme/
        │   ├── kinetix_theme.dart
        │   └── chart_theme.dart
        └── widgets/
            ├── glass_card.dart         # Glassmorphism card (RepaintBoundary-safe)
            ├── map_view.dart           # flutter_map + CartoCDN + zoom
            ├── dashboard_route_panel.dart
            ├── risk_alerts_panel.dart
            ├── route_optimization_cards.dart
            ├── weight_sliders.dart
            ├── shimmer_loading.dart
            ├── error_retry.dart
            ├── opaque_data_text.dart
            └── responsive_layout.dart
```

---

## Getting Started

### Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | [python.org](https://python.org) |
| Flutter | 3.x | [flutter.dev](https://flutter.dev/docs/get-started/install) |
| Chrome | any | for Flutter Web |
| Hugging Face account | — | [huggingface.co](https://huggingface.co) — optional, for AI explanations |

### Backend Setup

```bash
# 1. Navigate to the backend directory
cd backend

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Set your Hugging Face token for AI explanations
#    Create backend/.env with:
#    HF_API_TOKEN=hf_your_token_here

# 5. Start the server
uvicorn app.main:app --reload
```

The backend starts on **http://localhost:8000**.

> **Important:** Run `uvicorn` from inside the `backend/` directory. Running from the project root causes `ModuleNotFoundError: No module named 'app'`.

Verify it's running:
```bash
curl http://localhost:8000/api/health
# {"status":"success","data":{"service":"kinetix-ai","version":"0.1.0"},...}
```

Interactive API docs: **http://localhost:8000/docs**

### Frontend Setup

```bash
# 1. Navigate to the frontend directory
cd frontend

# 2. Install Flutter dependencies
flutter pub get

# 3. Run in Chrome
flutter run -d chrome
```

> **After any `pubspec.yaml` change** (e.g. adding assets), always run `flutter pub get` and do a **full restart** (not hot reload) — the asset manifest is only regenerated on full restart.

### Running the Full System

Open **two terminals**:

**Terminal 1 — Backend:**
```bash
cd backend
uvicorn app.main:app --reload
```

**Terminal 2 — Frontend:**
```bash
cd frontend
flutter run -d chrome
```

Log in with **any username and password** — the mock auth endpoint accepts all credentials.

---

## API Reference

All responses follow a consistent envelope:

```json
{
  "status": "success" | "error",
  "data": { ... },
  "error": null | { "code": "string", "message": "string" },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/shipments` | List all active shipments |
| `GET` | `/api/shipments/{id}` | Shipment detail with timeline |
| `GET` | `/api/alerts` | Active risk alerts |
| `POST` | `/api/optimize` | Compute optimal routes |
| `POST` | `/api/explain` | Generate NL explanation (Gemma 4B) |
| `GET` | `/api/analytics?time_range=` | Aggregate analytics (24h / 7d / 30d) |
| `GET` | `/api/settings` | Get SLA/penalty/weight settings |
| `PUT` | `/api/settings` | Update settings |
| `POST` | `/api/auth/login` | Mock login (any credentials) |
| `POST` | `/api/auth/logout` | Logout |
| `POST` | `/api/demo/trigger-disruption` | Force HIGH-severity alert |

**Example — optimize routes:**
```bash
curl -X POST http://localhost:8000/api/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "shipment_id": "SHP-001",
    "weights": {"cost": 0.4, "time": 0.3, "carbon": 0.2, "risk": 0.1}
  }'
```

**Example — explain a route:**
```bash
curl -X POST http://localhost:8000/api/explain \
  -H "Content-Type: application/json" \
  -d '{
    "route": { "label": "cheapest", "waypoints": ["Shanghai", "Singapore", "LA"], ... },
    "alternatives": [...]
  }'
# Returns: { "explanation": "...", "source": "model" | "fallback" }
```

---

## ML Services

### Disruption Detector

| Property | Value |
|----------|-------|
| Algorithm | `sklearn.ensemble.IsolationForest` |
| Config | `n_estimators=100`, `contamination=0.1`, `random_state=42` |
| Features | location deviation (km), time deviation (ratio), weather severity (0–3), historical delay frequency (0–1) |
| Training | Pre-fitted on 1,000 synthetic normal samples at startup |
| Severity | score < −0.3 → HIGH · [−0.3, −0.15) → MEDIUM · [−0.15, 0) → LOW |
| SLA | < 2 seconds per shipment |

### ETA Predictor

| Property | Value |
|----------|-------|
| Algorithm | `xgboost.XGBRegressor` |
| Config | `n_estimators=200`, `max_depth=6`, `learning_rate=0.1` |
| Features (18) | origin/dest/current coords, distance remaining, completion %, one-hot weather (4), hour sin/cos, day sin/cos, delay minutes, historical avg hours |
| Training | Pre-trained on 500 synthetic samples at startup; persisted to `models/eta_model.json` |
| Confidence interval | ±1 residual standard deviation (~80% coverage) |
| Fallback | `historical_avg_hours ± 20%` if model unavailable |
| SLA | < 3 seconds |

### Optimization Engine

| Property | Value |
|----------|-------|
| Algorithm | NetworkX `DiGraph` + `all_simple_paths(cutoff=6)` |
| Graph | 22 nodes (ports, warehouses, distribution centers, customs), 58 directed edges |
| Edge attributes | `cost_usd`, `time_hours`, `carbon_kg`, `risk_score`, `transport_mode` |
| Scoring | `Score = w_cost × Σnorm_cost + w_time × Σnorm_time + w_carbon × Σnorm_carbon + w_risk × max(norm_risk)` |
| Normalization | Min-max across all graph edges before applying weights |
| Output | Top 3 routes labeled cheapest / fastest / greenest / safest; lowest-score route marked `is_recommended` |
| SLA | < 3 seconds |

### Reasoning Engine

| Property | Value |
|----------|-------|
| Model | `google/gemma-4-31B-it` |
| API | Hugging Face Router (`router.huggingface.co/v1/chat/completions`) |
| Timeout | 20 seconds |
| Fallback | Template-based explanation using route metrics |
| Word limit | 200 words (truncated if exceeded) |
| Response field | `source: "model" \| "fallback"` |
| Auth | `HF_API_TOKEN` environment variable (set in `backend/.env`) |

The Reasoning Engine uses the **OpenAI-compatible chat completions** endpoint of the HF Router, making it straightforward to swap `gemma-4-31B-it` for any other HF-hosted instruction-tuned model by changing `_DEFAULT_MODEL` in `reasoning_engine.py`.

---

## Frontend Pages

| Route | Page | Key Features |
|-------|------|-------------|
| `/` | Landing | Hero image, feature cards, CTA, floating overlays |
| `/login` | Login | Mock auth, glassmorphism card, error handling |
| `/dashboard` | Dashboard | Live CartoCDN map, risk alerts, weight sliders, zoom controls |
| `/dashboard/shipment/:id` | Shipment Detail | Bento grid, risk gauge, forecast chart, AI explanation, Generate Report / Manage Risk |
| `/analytics` | Analytics | Delay trends, cost savings (bar), carbon reduction (line), SLA gauge |
| `/settings` | Settings | Bento grid: SLA thresholds, risk sensitivity, conflict alert, penalty amounts, weight bias sliders |
| `/profile` | Profile | Edit profile sheet, security settings, theme preferences |
| `/solutions` | Solutions | Feature showcase |
| `/global-network` | Global Network | Network visualization |
| `/book-demo` | Book Demo | Demo request form |

All routes except `/` and `/login` are protected by an auth guard — unauthenticated users are redirected to `/login`.

---

## Design System

### Color Tokens

| Token | Dark Mode | Light Mode | Usage |
|-------|-----------|------------|-------|
| `colorPrimary` | `#0F172A` | `#FFFFFF` | Sidebar, top bar |
| `colorSecondary` | `#1E293B` | `#F8FAFC` | Cards, surfaces |
| `colorAccent` | `#22C55E` | `#22C55E` | CTAs, positive indicators |
| `colorBackground` | `#020617` | `#F1F5F9` | Page backgrounds |
| `colorText` | `#F8FAFC` | `#0F172A` | Primary text |
| `colorDanger` | `#EF4444` | `#EF4444` | HIGH alerts, errors |
| `colorWarning` | `#F59E0B` | `#F59E0B` | MEDIUM alerts |
| `colorInfo` | `#3B82F6` | `#3B82F6` | Created status, info |

### Typography

| Font | Usage |
|------|-------|
| Plus Jakarta Sans | Headings, body, UI labels |
| Fira Sans | Secondary headings, buttons |
| Fira Code | Numeric data, metrics, shipment IDs, chart axes |

### Glassmorphism

- `BackdropFilter` blur: 10–20px (clamped, default 16px)
- Dark: `rgba(card, 0.85)` background, `rgba(white, 0.1)` border
- Light: `rgba(white, 0.92)` background, `Colors.grey.shade200` border
- `OpaqueDataText` widget ensures critical numeric data always has a solid backing for WCAG 2.1 AA contrast (≥ 4.5:1)

### Responsive Breakpoints

| Breakpoint | Width | Layout |
|-----------|-------|--------|
| Mobile | < 768px | Single column, drawer sidebar |
| Tablet | 768–1024px | Two-column, compact sidebar (72px) |
| Desktop | > 1024px | Multi-column, full sidebar (288px) |

### Map Tiles

CartoCDN is used as the tile source for Flutter Web because it sends `Access-Control-Allow-Origin: *` on every response, which is required for CanvasKit's WebGL texture loader. `tile.openstreetmap.org` does **not** send CORS headers and cannot be used directly in Flutter Web.

| Theme | URL template |
|-------|-------------|
| Dark | `https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png` |
| Light | `https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png` |

Attribution: © OpenStreetMap contributors, © CARTO

---

## Configuration

### Backend — `backend/.env`

```env
# Hugging Face API token for the Reasoning Engine (google/gemma-4-31B-it)
# Get yours at: https://huggingface.co/settings/tokens
# If unset, the engine uses template-based fallback responses.
HF_API_TOKEN=hf_your_token_here
```

```bash
# Windows — set before starting uvicorn
set HF_API_TOKEN=hf_your_token_here
uvicorn app.main:app --reload

# macOS / Linux
HF_API_TOKEN=hf_your_token_here uvicorn app.main:app --reload
```

### Frontend — API Base URL

```dart
// frontend/lib/services/api_client.dart
BaseOptions(
  baseUrl: 'http://localhost:8000',  // ← change for production
  ...
)
```

### Frontend — Content Security Policy

`frontend/web/index.html` includes a CSP `<meta>` tag that allows:
- `script-src`: `https://www.gstatic.com` (Flutter CanvasKit)
- `img-src`: `https://*.basemaps.cartocdn.com`, `https://*.tile.openstreetmap.org`
- `connect-src`: `http://localhost:*` (backend), `https:`, `wss:`
- `font-src`: `https://fonts.gstatic.com`

---

## Testing

### Backend Tests

```bash
cd backend
python -m pytest tests/ -v
```

Coverage includes: data store CRUD, disruption detector (feature extraction, severity thresholds, batch), ETA predictor (features, confidence intervals, fallback), optimization engine (normalization, scoring, labeling, performance), reasoning engine (HF API success/failure, fallback, truncation), simulation loop (initialization, cycle, pool replenishment), all API endpoints via `TestClient`.

### Frontend Tests

```bash
cd frontend
flutter test
```

Coverage includes: all Dart models (fromJson/toJson round-trips), GlassCard, OpaqueDataText, ResponsiveLayout, ShimmerLoading, ErrorRetry, MapView (loading/error/data states), RiskAlertsPanel, RouteOptimizationCards, WeightSliders, LoginPage, DashboardPage (all three breakpoints), AuthNotifier.

---

## Development Notes

### AI Model — Gemma 4B via HF Router

The Reasoning Engine calls `router.huggingface.co/v1/chat/completions` with model `google/gemma-4-31B-it`. This endpoint is OpenAI API-compatible, so swapping to a different model (e.g. `meta-llama/Llama-3.1-8B-Instruct`) requires only changing `_DEFAULT_MODEL` in `backend/app/services/reasoning_engine.py`. The `.env` file in `backend/` is loaded automatically at startup — no shell export needed.

### Map Performance

The dashboard map uses a single `FlutterMap` instance with all layers as children (`TileLayer → PolylineLayer → MarkerLayer`). Using two separate `FlutterMap` instances (one for tiles, one for markers) causes independent viewports and breaks tile rendering. Both the map and the right-side panels are wrapped in `RepaintBoundary` to isolate their repaint cycles.

### Shipment Polling — No Loading Flash

`shipmentsProvider` is a `StateNotifierProvider` (not `FutureProvider`). Background 5-second polling updates `ShipmentsState.shipments` in-place. Consumers that only need coordinates use `ref.watch(shipmentListProvider)` (a derived `Provider` with `.select`) to avoid rebuilding when `isInitialLoading` or `error` changes.

### Asset Registration

Local images must be declared in `pubspec.yaml` under `flutter.assets` **and** `flutter pub get` must be run before they appear. After adding a new asset, do a **full restart** (not hot reload) — the dev server caches the old `AssetManifest.bin`.

```yaml
flutter:
  uses-material-design: true
  assets:
    - assets/images/hero.png
```

### In-Memory Storage

All data lives in Python dicts/lists — no database setup required. `DataStore` uses `threading.Lock` for write operations. This makes the system trivially runnable locally while still demonstrating concurrent request handling.

### XGBoost Model Persistence

On first startup, the ETA Predictor trains on 500 synthetic samples and saves to `models/eta_model.json`. Subsequent startups load the saved model. Delete the file to force retraining.

### Mock Authentication

The login endpoint accepts any username/password and returns a UUID token. The auth guard in `app_router.dart` checks `isAuthenticated` in `authProvider`. This is designed to be swapped for a real auth provider (Firebase, Supabase, etc.) without architectural changes.

### Flutter Web CORS

FastAPI uses `allow_origins=["*"]` so the Flutter web app can connect from any localhost port. Tighten this for production deployments.
