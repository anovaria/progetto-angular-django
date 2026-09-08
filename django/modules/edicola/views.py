from __future__ import annotations

from collections import Counter
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import EdicolaLog, EdicolaPrincipale
from .services import clear_all_dates, refresh_principale_from_goldreport


def _build_filtered_queryset(request: HttpRequest):
    q = (request.GET.get("q") or "").strip()
    only_neg = request.GET.get("neg") == "1"
    only_main = request.GET.get("main") == "1"
    only_has_date = request.GET.get("hasdate") == "1"

    qs = EdicolaPrincipale.objects.all()

    if q:
        numeric = None
        try:
            numeric = int(q)
        except Exception:
            numeric = None

        cond = (
            Q(sett__icontains=q)
            | Q(rep__icontains=q)
            | Q(srep__icontains=q)
            | Q(ccom__icontains=q)
            | Q(descc__icontains=q)
            | Q(descrart__icontains=q)
            | Q(stato__icontains=q)
            | Q(ean__icontains=q)
        )
        if numeric is not None:
            cond = cond | Q(codart=numeric)
        qs = qs.filter(cond)

    if only_neg:
        qs = qs.filter(giacenza_pdv__lt=0)

    if only_main:
        qs = qs.filter(eanprinc=1)

    if only_has_date:
        qs = qs.exclude(data__isnull=True)

    # Come Access: ordinamento alfabetico per descrizione articolo
    qs = qs.order_by("descrart", "codart", "ean")
    return q, only_neg, only_main, only_has_date, qs


def _build_dashboard_context(request: HttpRequest) -> dict:
    q, only_neg, only_main, only_has_date, qs = _build_filtered_queryset(request)

    total = EdicolaPrincipale.objects.count()
    neg = EdicolaPrincipale.objects.filter(giacenza_pdv__lt=0).count()
    updated_dtaaggio = (
        EdicolaPrincipale.objects.exclude(dtaaggio__isnull=True)
        .exclude(dtaaggio="")
        .order_by("-dtaaggio")
        .values_list("dtaaggio", flat=True)
        .first()
    )

    codart_main_counts = Counter(qs.filter(eanprinc=1).values_list("codart", flat=True))
    codart_green = {k for k, v in codart_main_counts.items() if v > 1}

    # Manteniamo page_obj per stabilità, ma di fatto mostriamo tutto in una sola "listbox"
    paginator = Paginator(qs, 50000)
    page_obj = paginator.get_page(1)

    return {
        "title": "Gestione Edicola",
        "total": total,
        "neg": neg,
        "updated_dtaaggio": updated_dtaaggio,
        "q": q,
        "only_neg": only_neg,
        "only_main": only_main,
        "only_has_date": only_has_date,
        "page_obj": page_obj,
        "codart_green": codart_green,
    }


def dashboard(request: HttpRequest) -> HttpResponse:
    ctx = _build_dashboard_context(request)
    return render(request, "edicola/dashboard.html", ctx)


def refresh(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return redirect("edicola:dashboard")

    res = refresh_principale_from_goldreport(limit=None)
    if res.ok:
        suffix = f" | Date preservate: {res.updated_dates}" if res.updated_dates else ""
        messages.success(
            request,
            f"Aggiornamento completato. Inseriti: {res.inserted}{suffix}",
        )
    else:
        messages.error(request, f"Aggiornamento fallito: {'; '.join(res.warnings)}")

    return redirect("edicola:dashboard")




def clear_dates(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return redirect("edicola:dashboard")

    cleared = clear_all_dates()
    messages.success(request, f"Date azzerate: {cleared} record.")
    return redirect("edicola:dashboard")


def save_edits(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return redirect("edicola:dashboard")

    row_ids = request.POST.getlist("row_ids")
    if not row_ids:
        messages.warning(request, "Nessuna modifica da salvare.")
        return redirect("edicola:dashboard")

    objects = {
        str(obj.id): obj
        for obj in EdicolaPrincipale.objects.filter(id__in=row_ids)
    }

    to_update = []
    errors = []

    for row_id in row_ids:
        obj = objects.get(str(row_id))
        if not obj:
            continue

        raw_price = (request.POST.get(f"prezzovend_{row_id}") or "").strip()
        raw_data = (request.POST.get(f"data_{row_id}") or "").strip()

        new_price = None
        if raw_price:
            try:
                new_price = Decimal(raw_price.replace(",", "."))
            except (InvalidOperation, ValueError):
                errors.append(f"Prezzo non valido per CODART {obj.codart}: {raw_price}")
                continue

        new_data = None
        if raw_data:
            parsed = parse_datetime(raw_data)
            if parsed is None:
                errors.append(f"Data non valida per CODART {obj.codart}: {raw_data}")
                continue
            if timezone.is_naive(parsed):
                new_data = timezone.make_aware(parsed, timezone.get_current_timezone())
            else:
                new_data = parsed

        changed = False
        if obj.prezzovend != new_price:
            obj.prezzovend = new_price
            changed = True
        if obj.data != new_data:
            obj.data = new_data
            changed = True

        if changed:
            to_update.append(obj)

    if to_update:
        EdicolaPrincipale.objects.bulk_update(to_update, ["prezzovend", "data"], batch_size=1000)
        messages.success(request, f"Salvate {len(to_update)} modifiche temporanee.")
    elif not errors:
        messages.info(request, "Nessuna modifica da salvare.")

    for err in errors[:5]:
        messages.error(request, err)
    if len(errors) > 5:
        messages.error(request, f"...e altri {len(errors) - 5} errori.")

    query = {}
    if request.POST.get("q"):
        query["q"] = request.POST.get("q")
    if request.POST.get("main") == "1":
        query["main"] = "1"
    if request.POST.get("neg") == "1":
        query["neg"] = "1"

    url = reverse("edicola:dashboard")
    if query:
        url = f"{url}?{urlencode(query)}"
    return redirect(url)


def articoli_list(request: HttpRequest) -> HttpResponse:
    # Manteniamo la rotta per compatibilità, ma la UI ora è unificata nella dashboard.
    return dashboard(request)


def log_list(request: HttpRequest) -> HttpResponse:
    logs = EdicolaLog.objects.all()
    paginator = Paginator(logs, 50000)
    page_obj = paginator.get_page(1)
    return render(request, "edicola/log_list.html", {"page_obj": page_obj})


def autosave_note(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Metodo non consentito."}, status=405)

    row_id = (request.POST.get("row_id") or "").strip()
    field = (request.POST.get("field") or "").strip()
    value = (request.POST.get("value") or "").strip()

    if field not in {"prezzovend", "data"}:
        return JsonResponse({"ok": False, "error": "Campo non valido."}, status=400)

    try:
        obj = EdicolaPrincipale.objects.get(pk=row_id)
    except EdicolaPrincipale.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Record non trovato."}, status=404)

    if field == "prezzovend":
        if value:
            try:
                new_value = Decimal(value.replace(",", "."))
            except (InvalidOperation, ValueError):
                return JsonResponse({"ok": False, "error": f"Prezzo non valido: {value}"}, status=400)
        else:
            new_value = None
    else:
        if value:
            parsed = parse_datetime(value)
            if parsed is None:
                return JsonResponse({"ok": False, "error": f"Data non valida: {value}"}, status=400)
            if timezone.is_naive(parsed):
                new_value = timezone.make_aware(parsed, timezone.get_current_timezone())
            else:
                new_value = parsed
        else:
            new_value = None

    setattr(obj, field, new_value)
    obj.save(update_fields=[field])
    return JsonResponse({"ok": True})
