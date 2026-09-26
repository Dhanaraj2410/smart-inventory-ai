from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from apps.accounts.permissions import role_required
from apps.accounts.models import User
from .models import SalesRecord, SalesImportLog
from .services import validate_and_import_csv


@login_required
def sales_list(request):
    records = SalesRecord.objects.select_related("product").order_by("-date")[:200]
    return render(request, "sales/list.html", {"records": records})


@login_required
@role_required(User.Role.ADMIN, User.Role.MANAGER)
def sales_upload(request):
    if request.method == "POST" and request.FILES.get("file"):
        f = request.FILES["file"]
        try:
            log = validate_and_import_csv(f, uploaded_by=request.user, file_name=f.name)
            messages.success(request, f"Imported {log.rows_created} sales rows "
                                       f"({log.rows_failed} failed) from {f.name}.")
        except ValueError as e:
            messages.error(request, str(e))
        return redirect("sales:upload")

    logs = SalesImportLog.objects.all()[:20]
    return render(request, "sales/upload.html", {"logs": logs})
