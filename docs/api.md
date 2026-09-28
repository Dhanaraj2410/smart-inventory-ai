# REST API quick reference

All API routes are under `/api/`. Endpoints require an authenticated user;
the configured authentication classes include Django session authentication.
Use the browsable API from a logged-in browser for interactive exploration.
Pagination uses page numbers with a default page size of 25.

## Routes

| Route | Purpose |
|---|---|
| `/api/products/` | Product records |
| `/api/categories/` | Product categories |
| `/api/suppliers/` | Suppliers |
| `/api/warehouses/` | Warehouses |
| `/api/sales/` | Sales records |
| `/api/predictions/` | Prediction history |
| `/api/predict/<product-id>/` | Predict stockout risk for one product |
| `/api/predictions/bulk/` | Bulk predictions |
| `/api/models/performance/` | Model evaluation records |
| `/api/models/train/` | Trigger model training |
| `/api/alerts/` | Inventory alerts |
| `/api/forecasts/` | Demand forecast records |
| `/api/forecast/<product-id>/` | Forecast demand for one product |
| `/api/recommendations/` | Reorder recommendations |
| `/api/recommendations/bulk/` | Bulk reorder recommendations |
| `/api/simulation/<product-id>/` | Simulate a product inventory scenario |
| `/api/dashboard/` | Dashboard metrics |
| `/api/ai/chat/` | Ask an inventory question |
| `/api/ai/summary/` | Generate an inventory summary |
| `/api/ai/product-insight/` | Get an AI-assisted product insight |

Product, sales, prediction, forecast, recommendation, and alert collections
are exposed through Django REST Framework viewsets. Consult the browsable API
or the corresponding `apps/*/api_views.py` for accepted methods, filters, and
request fields.

## Example

With a logged-in session cookie:

```http
GET /api/products/?search=headphones
```

```http
GET /api/predict/42/?horizon=7
```

The product ID and optional query parameters must refer to data in the
database. Each endpoint applies its own role permissions; consult the
corresponding `apps/*/api_views.py` before relying on a write operation.
