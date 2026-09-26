"""
Hugging Face AI service.

All Hugging Face API/model calls live here — never call the API directly
from a Django view (see apps/ai_assistant/views.py, which only calls the
functions in this module).

Design contract, per the project spec:
  * The LLM NEVER replaces the ML stockout/demand models for numeric
    predictions -- it only explains, summarizes, and answers questions
    about numbers that were already computed elsewhere and passed in here
    as `grounding_data`.
  * The LLM must never invent inventory numbers. Every prompt below embeds
    the retrieved database facts and instructs the model to only use them.
  * If HUGGINGFACE_API_KEY is not configured (e.g. running the eval/demo
    without external network access), every function below falls back to a
    deterministic, template-based natural-language generator built from the
    same grounding_data. This keeps the feature fully functional and still
    100% grounded even with no external API calls -- it just uses simpler
    (non-generative) phrasing instead of an LLM.
"""
import json
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

HF_API_URL = "https://api-inference.huggingface.co/models/{model}"


def _hf_configured():
    return bool(settings.HUGGINGFACE_API_KEY)


def _call_hf_text_generation(prompt, model=None, max_new_tokens=200):
    """Low-level call to the HF Inference API. Returns None on any failure
    so callers can fall back to the template-based generator -- the AI
    assistant must degrade gracefully, never crash the request."""
    if not _hf_configured():
        return None
    model = model or settings.HUGGINGFACE_MODEL
    try:
        resp = requests.post(
            HF_API_URL.format(model=model),
            headers={"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"},
            json={"inputs": prompt, "parameters": {"max_new_tokens": max_new_tokens, "temperature": 0.3}},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list) and data and "generated_text" in data[0]:
            return data[0]["generated_text"].strip()
        if isinstance(data, dict) and "generated_text" in data:
            return data["generated_text"].strip()
        return None
    except Exception as e:
        logger.warning("Hugging Face inference call failed, using fallback generator: %s", e)
        return None


# --------------------------------------------------------------------------
# A. Inventory Question Answering
# --------------------------------------------------------------------------
def answer_inventory_question(question, grounding_data):
    """`grounding_data` is a dict of already-retrieved, real DB facts
    relevant to the question (see apps/ai_assistant/retrieval.py). The model
    is instructed to answer ONLY from this data and to say so plainly when
    the data does not cover the question."""
    if not grounding_data or grounding_data.get("no_match"):
        return ("I couldn't find matching data in the current inventory for that question. "
                "Try asking about a specific product name/SKU, or about overall stockout risk, "
                "low-stock products, or reorder recommendations.")

    prompt = (
        "You are an inventory analyst assistant. Answer the user's question using ONLY the "
        "JSON facts provided below. Never invent numbers that are not present in the JSON. "
        "If the JSON does not contain enough information, say so plainly.\n\n"
        f"Facts (JSON):\n{json.dumps(grounding_data, default=str)}\n\n"
        f"Question: {question}\n\nAnswer concisely in 1-3 sentences:"
    )
    generated = _call_hf_text_generation(prompt)
    if generated:
        return generated
    return _template_answer(question, grounding_data)


def _template_answer(question, data):
    if "products" in data:
        items = data["products"]
        if not items:
            return "No products currently match that criteria."
        lines = []
        for p in items[:5]:
            lines.append(
                f"{p['name']} ({p['sku']}): current stock {p['current_stock']}, "
                f"status {p['stock_status']}" + (f", risk {p['risk_level']}" if p.get("risk_level") else "")
            )
        summary = f"{len(items)} product(s) match. " + "; ".join(lines) + "."
        return summary
    if "single_product" in data:
        p = data["single_product"]
        parts = [f"{p['name']} ({p['sku']}) currently has {p['current_stock']} units in stock, "
                 f"status: {p['stock_status']}."]
        if p.get("risk_level"):
            parts.append(f" Stockout risk is {p['risk_level']} ({p['probability']:.0%}).")
        if p.get("recommended_quantity") is not None:
            parts.append(f" Recommended reorder quantity: {p['recommended_quantity']} units.")
        return "".join(parts)
    return "I found some data but couldn't summarize it — please check the dashboard for details."


# --------------------------------------------------------------------------
# B. Inventory Summary
# --------------------------------------------------------------------------
def generate_inventory_summary(stats):
    """`stats` is a dict of real, DB-computed dashboard numbers."""
    prompt = (
        "Write a concise 2-3 sentence natural-language inventory summary using ONLY these facts "
        f"(JSON, do not invent other numbers): {json.dumps(stats, default=str)}"
    )
    generated = _call_hf_text_generation(prompt, max_new_tokens=120)
    if generated:
        return generated
    return (
        f"The warehouse currently has {stats.get('total_products', 0)} active products "
        f"totaling {stats.get('total_units', 0)} units. "
        f"{stats.get('low_stock', 0)} products are below their reorder point, "
        f"{stats.get('high_risk', 0)} have high stockout risk, and "
        f"{stats.get('out_of_stock', 0)} are currently out of stock."
    )


# --------------------------------------------------------------------------
# C. Prediction Explanation
# --------------------------------------------------------------------------
def explain_prediction(product_name, probability, current_stock, forecast, lead_time, factors=None):
    prompt = (
        "Explain in 1-2 plain-language sentences why this product has this stockout risk, using "
        "only the numbers given (do not invent additional causes beyond the listed factors):\n"
        f"Product: {product_name}\nStockout probability: {probability:.0%}\n"
        f"Current stock: {current_stock}\nForecasted demand: {forecast}\nLead time: {lead_time} days\n"
        f"Known factors: {factors or []}"
    )
    generated = _call_hf_text_generation(prompt, max_new_tokens=100)
    if generated:
        return generated
    if factors:
        factor_text = "; ".join(factors)
        return (f"{product_name} has a stockout probability of {probability:.0%} because: {factor_text}.")
    return (
        f"{product_name} has a stockout probability of {probability:.0%}. Current stock ({current_stock}) "
        f"compared against forecasted demand ({forecast}) and a {lead_time}-day supplier lead time drives this."
    )


# --------------------------------------------------------------------------
# D. Product Categorization
# --------------------------------------------------------------------------
CANDIDATE_CATEGORIES = [
    "Electronics", "Audio", "Computing", "Mobile Accessories", "Home & Kitchen",
    "Apparel", "Office Supplies", "Furniture", "Sporting Goods", "Toys & Games",
    "Health & Beauty", "Automotive", "Grocery", "Tools & Hardware", "Books & Media",
]


def classify_product_description(description):
    """Zero-shot style classification. Uses the HF Inference API
    (zero-shot-classification pipeline) when configured; otherwise falls
    back to simple keyword matching against CANDIDATE_CATEGORIES so the
    feature still returns a (lower-confidence, clearly labeled) suggestion."""
    if _hf_configured():
        try:
            resp = requests.post(
                HF_API_URL.format(model=settings.HUGGINGFACE_CLASSIFIER_MODEL),
                headers={"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"},
                json={"inputs": description, "parameters": {"candidate_labels": CANDIDATE_CATEGORIES}},
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
            if "labels" in data:
                return {"category": data["labels"][0], "confidence": round(data["scores"][0], 3),
                         "alternatives": list(zip(data["labels"][1:4], data["scores"][1:4])),
                         "source": "huggingface"}
        except Exception as e:
            logger.warning("HF classification failed, using keyword fallback: %s", e)

    text = description.lower()
    scores = {cat: sum(1 for w in cat.lower().split() if w in text) for cat in CANDIDATE_CATEGORIES}
    keyword_map = {
        "Audio": ["headphone", "speaker", "earbud", "bluetooth", "sound"],
        "Computing": ["laptop", "keyboard", "mouse", "monitor", "cpu", "ssd"],
        "Mobile Accessories": ["phone case", "charger", "cable", "power bank"],
        "Apparel": ["shirt", "jacket", "shoe", "jeans", "dress"],
        "Home & Kitchen": ["kitchen", "cookware", "blender", "furniture", "sofa"],
    }
    for cat, kws in keyword_map.items():
        scores[cat] += sum(2 for kw in kws if kw in text)
    best = max(scores, key=scores.get)
    confidence = min(0.6, 0.2 + 0.1 * scores[best])
    return {"category": best if scores[best] > 0 else "General",
            "confidence": round(confidence, 2), "alternatives": [], "source": "keyword_fallback"}
