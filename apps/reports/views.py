import csv
import io
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render

from apps.products.models import Product
from apps.predictions.services import bulk_predict
from apps.recommendations.services import bulk_recommendations
from apps.dashboard.services import get_dashboard_stats, get_category_analysis, get_top_risk_products

REPORT_SECTIONS = [
    ("inventory_summary", "Inventory Summary"),
    ("stockout_risk", "Stockout Risk"),
    ("demand_forecast", "Demand Forecast"),
    ("reorder_recommendations", "Reorder Recommendations"),
    ("overstock_analysis", "Overstock Analysis"),
    ("top_products", "Top Products"),
]


@login_required
def report_builder(request):
    return render(request, "reports/builder.html", {"sections": REPORT_SECTIONS})


@login_required
def generate_report(request):
    selected = request.GET.getlist("section") or [s[0] for s in REPORT_SECTIONS]
    fmt = request.GET.get("format", "csv")

    data = {}
    if "inventory_summary" in selected:
        data["inventory_summary"] = get_dashboard_stats()
    if "stockout_risk" in selected:
        data["stockout_risk"] = bulk_predict(persist=False)
    if "reorder_recommendations" in selected:
        data["reorder_recommendations"] = bulk_recommendations()
    if "overstock_analysis" in selected:
        data["overstock_analysis"] = [p for p in Product.objects.filter(is_active=True)
                                       if p.stock_status == "OVERSTOCKED"]
    if "top_products" in selected:
        data["top_products"] = get_top_risk_products(15)

    if fmt == "pdf":
        return _render_pdf(data)
    return _render_csv(data)


def _render_csv(data):
    output = io.StringIO()
    writer = csv.writer(output)
    for section, rows in data.items():
        writer.writerow([f"=== {section.upper()} ==="])
        if isinstance(rows, dict):
            for k, v in rows.items():
                writer.writerow([k, v])
        elif isinstance(rows, list):
            for row in rows:
                if hasattr(row, "sku"):
                    writer.writerow([row.sku, row.name, row.current_stock, row.stock_status])
                elif isinstance(row, dict):
                    writer.writerow(list(row.values()))
        writer.writerow([])

    response = HttpResponse(output.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="inventory_report.csv"'
    return response


def _render_pdf(data):
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter
    y = height - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Smart Inventory AI - Report")
    y -= 30
    c.setFont("Helvetica", 10)
    for section, rows in data.items():
        if y < 80:
            c.showPage()
            y = height - 50
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, section.replace("_", " ").title())
        y -= 18
        c.setFont("Helvetica", 9)
        if isinstance(rows, dict):
            for k, v in rows.items():
                c.drawString(60, y, f"{k}: {v}")
                y -= 13
                if y < 50:
                    c.showPage()
                    y = height - 50
        elif isinstance(rows, list):
            for row in rows[:40]:
                text = str(row)[:110]
                c.drawString(60, y, text)
                y -= 13
                if y < 50:
                    c.showPage()
                    y = height - 50
        y -= 10
    c.save()
    buf.seek(0)
    response = HttpResponse(buf.read(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="inventory_report.pdf"'
    return response
