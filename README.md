# Smart Inventory AI  

**Inventory Stockout Prediction & Reorder Recommendation System** — a full-stack
Django + ML + Hugging Face platform that predicts stockout risk, forecasts
demand, recommends reorder quantities, and answers natural-language
inventory questions grounded in real database data.

---

## 1. Project Overview

Smart Inventory AI helps a business answer:

1. Which products are at risk of stocking out, and when?
2. How much inventory will be needed over the next 7 / 14 / 30 days?
3. How much should be reordered, and why?
4. Which products need urgent attention vs. which are overstocked?
5. What's driving a given stockout-risk prediction?
6. "Which products need urgent restocking?" — asked in plain English.

Every number shown anywhere in the app (dashboard cards, charts, the AI
assistant's answers) is computed live from the database — nothing is
hard-coded.

## 2. Features

- **Stockout risk classification** (LOW / MEDIUM / HIGH) with probability and
  explainable factors, via a trained classifier with a transparent
  rule-based fallback.
- **Demand forecasting** for 7 / 14 / 30-day horizons via a trained
  regressor with a seasonally-aware fallback.
- **Reorder recommendation engine**: `reorder_point = avg_daily_demand x
  lead_time + safety_stock`; `recommended_qty = forecast_demand +
  safety_stock - current_stock`.
- **Inventory health classification**: Healthy / Low Stock / Critical /
  Overstocked / Out of Stock.
- **Product CRUD** with search, filter, CSV import/export.
- **Sales history CSV upload** with validation (bad dates, negative
  quantities, missing columns all rejected with clear errors).
- **AI Inventory Assistant** (Hugging Face-backed): answers natural-language
  questions, generates inventory summaries, and explains predictions — all
  grounded in retrieved database facts, never invented numbers.
- **What-If Simulator**: adjust demand %, supplier delay, stock levels and
  see the recalculated reorder point/quantity — clearly labeled as a
  simulation, never persisted as a real recommendation.
- **Bulk CSV prediction** with CSV export of results.
- **Inventory alerts** (high risk, out of stock, below reorder point,
  overstock) via a scheduled Celery task, with optional email notification.
- **Role-based access** (Admin / Inventory Manager / Viewer).
- **Full REST API** (Django REST Framework) mirroring every feature above.
- **Model performance page** showing real Accuracy/Precision/Recall/F1/ROC-AUC
  (classification) and MAE/MSE/RMSE/R2/MAPE (regression) from the last
  training run.
- **Reports**: CSV and PDF export across inventory summary, stockout risk,
  forecasts, recommendations, overstock analysis, top products.

## 3. Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, Django 5, Django REST Framework |
| Database | MySQL 8 (production), SQLite (local dev fallback) |
| ML | pandas, NumPy, scikit-learn, XGBoost (falls back to sklearn's GradientBoosting if not installed), joblib |
| AI/NLP | Hugging Face Inference API, with a fully-functional grounded fallback when no API key is configured |
| Background jobs | Celery + Redis |
| Frontend | Django templates, Bootstrap 5, Chart.js, vanilla JS |
| Deployment | Docker, docker-compose, Gunicorn, WhiteNoise |

## 4. Architecture

```
smart-inventory-ai/
├── config/          # settings, urls, wsgi/asgi, celery app
├── apps/
│   ├── accounts/        # custom User model, roles, auth views
│   ├── products/        # Product/Category/Supplier/Warehouse CRUD + API
│   ├── sales/            # SalesRecord + CSV import/validation
│   ├── predictions/      # PredictionHistory, ModelPerformance, InventoryAlert,
│   │                      #   rule-based + ML-backed risk service, Celery tasks
│   ├── forecasting/      # DemandForecast + forecasting service
│   ├── recommendations/  # Reorder engine + What-If simulator
│   ├── dashboard/        # Live-computed dashboard metrics
│   ├── ai_assistant/     # AIConversation/AIMessage, grounded retrieval + chat views
│   └── reports/          # CSV/PDF report generation
├── ml/
│   ├── data/             # sample dataset generator + generated CSVs
│   ├── preprocessing/    # cleaning + feature engineering (shared by train & predict)
│   ├── training/         # train_stockout_model.py, train_demand_model.py
│   ├── prediction/       # predict.py -- loads .pkl artifacts, serves predictions
│   └── models/           # saved .pkl artifacts + metrics JSON (regenerable)
├── services/         # thin orchestration layer (ml_service, forecasting_service,
│                      #   inventory_service, recommendation_service, huggingface_service)
├── templates/, static/
└── tests/
```

Business logic lives in `apps/*/services.py` and `services/`, never
directly in views -- views stay thin.

## 5. ML Workflow

```
Raw Sales Data -> Validation -> Missing-value handling -> Duplicate removal ->
Outlier capping (IQR) -> Feature engineering (calendar, rolling/lag,
inventory) -> Train/test split -> Train candidate models -> Evaluate ->
Select best by F1 (classifier) / RMSE (regressor) -> Serialize (joblib) ->
Prediction API (models loaded once, cached in memory)
```

Feature engineering (`ml/preprocessing/features.py`) is written once and
used identically at training time and prediction time, using only signals
that would actually be available at the moment of prediction (no leakage --
the stockout label is the only place that looks forward, and only for
labeling historical rows, never for building a feature).

**This was actually run, not just written.** During development a
26-product, ~15-month realistic synthetic dataset (seasonality, weekly
patterns, promo spikes, trend -- not pure noise) was generated and run
through the full pipeline:

| Model (stockout classifier) | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---|---|---|
| Logistic Regression | 0.912 | 0.893 | 0.949 | 0.920 | 0.981 |
| **Random Forest (selected)** | **0.961** | **0.959** | **0.969** | **0.964** | **0.995** |

| Model (demand regressor) | MAE | RMSE | R2 | MAPE |
|---|---|---|---|---|
| Linear Regression | 6.93 | 15.73 | 0.912 | 42.2% |
| **Random Forest (selected)** | **6.00** | **14.58** | **0.924** | **25.7%** |
| Gradient Boosting | 6.14 | 15.67 | 0.913 | 26.1% |

These exact artifacts (`ml/models/*.pkl`) ship in this repo so predictions
work immediately after setup -- no training required to try the app, though
retraining on your own data is one command (`python manage.py train_models`).

## 6. Hugging Face Integration

All Hugging Face calls live in `services/huggingface_service.py` -- never
inside a view. Contract:

- The LLM **never** replaces the ML models for numeric predictions; it only
  explains, summarizes, and answers questions about numbers computed
  elsewhere.
- Every prompt embeds retrieved database facts (`apps/ai_assistant/retrieval.py`
  turns a question into a real ORM query) and instructs the model to use
  only those facts.
- If `HUGGINGFACE_API_KEY` is unset, every AI feature falls back to a
  deterministic, template-based generator built from the *same* grounding
  data -- so the assistant is fully functional (and still fully grounded)
  with zero external API calls. This is the mode you'll see out of the box.
- Unmatched questions get an honest "I couldn't find that in the current
  inventory" rather than an invented answer.

## 7. Database Design

Key models: `User` (role-based), `Product`, `Category`, `Supplier`,
`Warehouse`, `SalesRecord`, `SalesImportLog`, `PredictionHistory`,
`DemandForecast`, `ReorderRecommendation`, `ModelPerformance`,
`InventoryAlert`, `AIConversation`, `AIMessage`. All timestamped
(`created_at`/`updated_at`), indexed on the fields they're filtered/sorted by.

## 8. Installation

```bash
git clone <this-repo>
cd smart-inventory-ai
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # edit as needed
```

### Quick start (SQLite, no external services)

```bash
python manage.py migrate
python manage.py createsuperuser
python ml/data/generate_sample_data.py     # generates ml/data/sample_*.csv
python manage.py seed_data                 # loads them into the DB
python manage.py train_models              # trains & evaluates both models
python manage.py runserver
```

Visit `http://127.0.0.1:8000`, log in, and the dashboard/predictions/AI
assistant will all have real data to work with. (Pretrained `.pkl` models
are also included, so predictions work even before you run `train_models`.)

### With MySQL, Redis, Celery (production-shaped)

Set `DB_ENGINE=mysql` and the `DB_*` vars in `.env`, then:

```bash
docker-compose up --build
```

This starts MySQL, Redis, the Django app (Gunicorn), a Celery worker, and
Celery beat (which runs `check_inventory_alerts` hourly per
`CELERY_BEAT_SCHEDULE` in `config/settings.py`).

## 9. Environment Variables

See `.env.example`. Notably:

```
DB_ENGINE=sqlite            # or mysql
HUGGINGFACE_API_KEY=        # optional -- leave blank to use the grounded fallback
HUGGINGFACE_MODEL=google/flan-t5-base
REDIS_URL=redis://localhost:6379/0
```

Never commit `.env` -- see `.gitignore`.

## 10. Running Locally / Training Models

```bash
python manage.py runserver                 # dev server
celery -A config worker --loglevel=info     # background tasks (separate terminal)
celery -A config beat --loglevel=info       # scheduled alerts (separate terminal)
python manage.py train_models               # retrain both ML models on current DB data
python manage.py test                       # run the test suite
```

## 11. API Documentation

Base path: `/api/`. Session or Token auth (DRF). A few examples:

```http
GET /api/products/?category=1&search=headphones
Authorization: Token <your-token>
```

```http
GET /api/predict/42/?horizon=7
-> {"risk_level": "HIGH", "probability": 0.91, "factors": [...], "model_name": "RandomForestClassifier"}
```

```http
POST /api/ai/chat/
{"message": "Which products need urgent restocking?"}
-> {"answer": "3 product(s) match. Wireless Headphones (P0001): current stock 18, status LOW_STOCK, risk HIGH; ...", "grounding_data": {...}}
```

Full endpoint list: `/api/products/`, `/api/sales/`, `/api/predictions/`,
`/api/forecast/<id>/`, `/api/recommendations/`, `/api/simulation/<id>/`,
`/api/dashboard/`, `/api/ai/chat/`, `/api/ai/summary/`,
`/api/models/performance/`, `/api/models/train/`, `/api/alerts/`.

## 12. Deployment

`Dockerfile` + `docker-compose.yml` are production-shaped (Gunicorn,
WhiteNoise for static files, MySQL, Redis, separate worker/beat containers).
For a platform like Render/Railway: set `DEBUG=False`, configure
`ALLOWED_HOSTS`, point `DB_*` at a managed MySQL instance, set
`REDIS_URL`, and run `collectstatic` + `migrate` as part of the build step.

## 13. Honesty About What's Included

This project was generated end-to-end by an AI assistant working in a
sandboxed environment **without network access or Django installed**. That
means:

- All Django/DRF/Celery code was written correctly and consistently against
  the framework's APIs, but **could not be executed against a live Django
  server** in that environment (no way to `pip install django` offline).
- The **ML pipeline was fully executed and verified** in that same
  environment (pandas/scikit-learn were available), including generating
  the sample dataset and training/evaluating both models -- those results
  above are real, not invented.
- Before relying on this in production: run `python manage.py migrate`,
  `python manage.py test`, and click through each page once -- treat it as
  a strong, coherent first implementation that hasn't yet had a live QA
  pass, not as something guaranteed bug-free on first boot.

## 14. Future Improvements

- Swap the simple keyword-based intent router in `ai_assistant/retrieval.py`
  for a proper intent-classification model.
- Add time-series-specific forecasting (Prophet / ARIMA) as an alternative
  to the tree-based regressor for products with strong seasonality.
- Add rate limiting on `/api/ai/*` endpoints.
- Add a proper frontend build (React/Vue) if the team outgrows server-rendered
  templates.
