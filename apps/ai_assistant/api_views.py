from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import AIConversation, AIMessage
from .retrieval import retrieve_for_question
from services.huggingface_service import answer_inventory_question, generate_inventory_summary


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def chat_api(request):
    question = request.data.get("message", "").strip()
    conversation_id = request.data.get("conversation_id")
    if not question:
        return Response({"error": "message is required"}, status=400)

    if conversation_id:
        conversation = AIConversation.objects.filter(pk=conversation_id, user=request.user).first()
    else:
        conversation = None
    if conversation is None:
        conversation = AIConversation.objects.create(user=request.user, title=question[:60])

    AIMessage.objects.create(conversation=conversation, role=AIMessage.Role.USER, content=question)
    grounding_data = retrieve_for_question(question)
    answer = answer_inventory_question(question, grounding_data)
    AIMessage.objects.create(conversation=conversation, role=AIMessage.Role.ASSISTANT,
                              content=answer, grounding_data_json=grounding_data)

    return Response({
        "conversation_id": conversation.id, "answer": answer, "grounding_data": grounding_data,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def summary_api(request):
    from apps.dashboard.services import get_dashboard_stats
    stats = get_dashboard_stats()
    return Response({"summary": generate_inventory_summary(stats), "stats": stats})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def classify_product_api(request):
    from services.huggingface_service import classify_product_description
    description = request.data.get("description", "")
    if not description:
        return Response({"error": "description is required"}, status=400)
    return Response(classify_product_description(description))
