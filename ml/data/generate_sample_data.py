"""
Generates a realistic sample dataset so the app works immediately after setup:
  ml/data/sample_products.csv  - product reference data
  ml/data/sample_sales.csv     - ~15 months of daily sales history per product

Sales are NOT pure random noise: each product has a base demand level, a
weekly seasonality pattern (weekday/weekend effect), a slow trend
(growing/declining/flat), and occasional promo/demand-spike events, plus
Poisson noise around that signal -- so the resulting series has the kind of
autocorrelation and seasonality a forecasting model can actually learn from.

Run directly:  python ml/data/generate_sample_data.py
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RNG = np.random.default_rng(42)

CATEGORIES = {
    "Electronics": ["Wireless Headphones", "Bluetooth Speaker", "4K Monitor", "Mechanical Keyboard",
                    "Wireless Mouse", "USB-C Hub", "Portable SSD 1TB", "Smartwatch"],
    "Home & Kitchen": ["Stainless Steel Blender", "Air Fryer", "Ceramic Cookware Set", "Robot Vacuum",
                       "Electric Kettle", "Coffee Maker"],
    "Apparel": ["Men's Running Shoes", "Women's Yoga Pants", "Unisex Hoodie", "Denim Jacket"],
    "Office Supplies": ["Ergonomic Office Chair", "Standing Desk", "Notebook 3-Pack", "Desk Organizer"],
    "Sporting Goods": ["Yoga Mat", "Adjustable Dumbbell Set", "Resistance Bands Kit", "Water Bottle 1L"],
}

SUPPLIERS = ["Global Supply Co", "Pacific Trading Ltd", "Northline Distributors", "Evergreen Wholesale"]
WAREHOUSES = ["Main Warehouse", "West Coast DC", "East Coast DC"]

START_DATE = pd.Timestamp("2025-06-01")
END_DATE = pd.Timestamp("2026-09-01")


def _demand_profile(base, trend_per_day, weekend_mult, day_index):
    trend = base + trend_per_day * day_index
    return max(trend, 0.5)


def generate():
    products = []
    sales_rows = []
    n_days = (END_DATE - START_DATE).days + 1
    dates = pd.date_range(START_DATE, END_DATE, freq="D")

    product_id = 1
    for category, names in CATEGORIES.items():
        for name in names:
            sku = f"P{product_id:04d}"
            base_demand = RNG.uniform(4, 30)
            trend_per_day = RNG.uniform(-0.01, 0.02) * base_demand
            weekend_mult = RNG.uniform(1.1, 1.6)
            unit_price = round(RNG.uniform(9.99, 349.99), 2)
            supplier = SUPPLIERS[RNG.integers(0, len(SUPPLIERS))]
            warehouse = WAREHOUSES[RNG.integers(0, len(WAREHOUSES))]
            lead_time = int(RNG.integers(3, 15))
            safety_stock = int(base_demand * RNG.uniform(2, 5))
            minimum_stock = int(base_demand * lead_time * 0.6)
            maximum_stock = int(base_demand * 45)

            promo_days = set(RNG.choice(n_days, size=max(1, n_days // 90), replace=False))

            daily_sold = []
            for i, d in enumerate(dates):
                mean = _demand_profile(base_demand, trend_per_day, weekend_mult, i)
                if d.dayofweek >= 5:
                    mean *= weekend_mult
                month = d.month
                if month in (11, 12):
                    mean *= 1.35
                elif month in (1, 2):
                    mean *= 0.85
                if i in promo_days:
                    mean *= RNG.uniform(2.0, 3.5)
                qty = RNG.poisson(lam=max(mean, 0.1))
                daily_sold.append(qty)
                sales_rows.append({
                    "date": d.strftime("%Y-%m-%d"), "product_id": sku,
                    "quantity_sold": int(qty), "unit_price": unit_price, "warehouse": warehouse,
                })

            recent_avg = np.mean(daily_sold[-30:])
            current_stock = int(max(0, recent_avg * lead_time * RNG.uniform(0.3, 2.2)))

            products.append({
                "sku": sku, "name": name, "category": category, "supplier": supplier,
                "warehouse": warehouse, "current_stock": current_stock,
                "minimum_stock": minimum_stock, "maximum_stock": maximum_stock,
                "safety_stock": safety_stock, "supplier_lead_time": lead_time,
                "unit_price": unit_price,
            })
            product_id += 1

    products_df = pd.DataFrame(products)
    sales_df = pd.DataFrame(sales_rows)

    products_path = os.path.join(HERE, "sample_products.csv")
    sales_path = os.path.join(HERE, "sample_sales.csv")
    products_df.to_csv(products_path, index=False)
    sales_df.to_csv(sales_path, index=False)
    return products_df, sales_df, products_path, sales_path


if __name__ == "__main__":
    products_df, sales_df, products_path, sales_path = generate()
    print(f"Generated {len(products_df)} products -> {products_path}")
    print(f"Generated {len(sales_df)} sales rows ({sales_df['date'].min()} to {sales_df['date'].max()}) -> {sales_path}")
    print("\nSample products:")
    print(products_df.head(5).to_string(index=False))
    print("\nSample sales:")
    print(sales_df.head(5).to_string(index=False))
