# REST API quick reference

All API routes are under `/api/`. Endpoints require an authenticated user;
the configured authentication classes include Django session authentication.
Use the browsable API from a logged-in browser for interactive exploration.
Pagination uses page numbers with a default page size of 25.

## Routes

| Route | Purpose |
|---|---|
| `/api/products/` | Product records |
| `/api/products/<product-id>/stock-adjustments/` | Read or create stock adjustment history |
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

## Inventory adjustments

Authenticated users can read the paginated adjustment history for an active
product. Inventory managers and admins can also submit stock corrections:

```http
POST /api/products/42/stock-adjustments/
Content-Type: application/json

{
  "quantity_change": -3,
  "note": "Damaged units removed during cycle count"
}
```

`quantity_change` is a nonzero signed whole number: positive values add stock
and negative values remove it. The required note is limited to 500 characters.
An adjustment that would reduce stock below zero is rejected with HTTP 400.
Successful writes return HTTP 201 with the adjustment ID, product, quantity
change, stock before and after, note, creator, and timestamp. The update and
audit record are written atomically.

Read history with `GET /api/products/42/stock-adjustments/?page=2`. Results
use the standard page-number pagination envelope (25 records per page).
Viewers may read the history but cannot create adjustments.
In the web UI, inventory managers can adjust stock from a product detail page;
any authenticated user can search the full history at `/products/adjustments/`
and export the current search as CSV.

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
