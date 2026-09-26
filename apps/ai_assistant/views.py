from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect

from .models import AIConversation, AIMessage
from .retrieval import retrieve_for_question
from services.huggingface_service import answer_inventory_question, generate_inventory_summary


@login_required
def chat_view(request, conversation_id=None):
    if conversation_id:
        conversation = get_object_or_404(AIConversation, pk=conversation_id, user=request.user)
    else:
        conversation = AIConversation.objects.create(user=request.user, title="New conversation")

    if request.method == "POST":
        question = request.POST.get("message", "").strip()
        if question:
            AIMessage.objects.create(conversation=conversation, role=AIMessage.Role.USER, content=question)
            grounding_data = retrieve_for_question(question)
            answer = answer_inventory_question(question, grounding_data)
            AIMessage.objects.create(conversation=conversation, role=AIMessage.Role.ASSISTANT,
                                      content=answer, grounding_data_json=grounding_data)
            if conversation.title in ("", "New conversation"):
                conversation.title = question[:60]
                conversation.save(update_fields=["title"])
        return redirect("ai_assistant:chat", conversation_id=conversation.id)

    conversations = AIConversation.objects.filter(user=request.user)[:20]
    messages_qs = conversation.messages.all()
    return render(request, "ai_assistant/chat.html", {
        "conversation": conversation, "conversations": conversations, "chat_messages": messages_qs,
    })


@login_required
def product_insight(request, pk):
    from apps.products.models import Product
    from apps.predictions.services import get_latest_risk
    from apps.forecasting.services import get_latest_forecast
    from services.huggingface_service import explain_prediction

    product = get_object_or_404(Product, pk=pk)
    risk = get_latest_risk(product)
    forecast = get_latest_forecast(product, horizon=7)
    insight = explain_prediction(
        product.name, risk.probability, product.current_stock,
        round(sum(forecast["values"]), 1), product.supplier_lead_time, risk.factors_json,
    )
    return render(request, "ai_assistant/insight_fragment.html", {
        "product": product, "risk": risk, "insight": insight,
    })
