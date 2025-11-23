"""
Views for the clientes app with enhanced filtering and presentation.
"""
from __future__ import annotations

import csv
from contextlib import suppress
from datetime import timedelta
from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import FieldError, ValidationError
from django.db.models import Count, Max, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import ClienteForm
from .models import Cliente


def annotate_cliente_queryset(qs):
    with suppress(FieldError):
        qs = qs.annotate(vehiculos_count=Count("vehiculos", distinct=True))
    with suppress(FieldError):
        qs = qs.annotate(citas_count=Count("citas", distinct=True))
    with suppress(FieldError):
        qs = qs.annotate(ultima_cita=Max("citas__fecha_inicio"))
    return qs


class ClienteFilterMixin:
    """Shared filtering logic for clientes."""

    paginate_by = 15

    def get_filter_values(self):
        request = self.request
        self.search_query = (request.GET.get("q") or "").strip()
        self.tipo_filter = (request.GET.get("tipo") or "").strip().lower()
        self.origen_filter = (request.GET.get("origen") or "").strip()
        self.estado_filter = (request.GET.get("estado") or "").strip().lower()
        self.order = (request.GET.get("o") or "").strip()
        self.now = timezone.now()
        self.reciente_threshold = self.now - timedelta(days=30)
        self.inactivo_threshold = self.now - timedelta(days=90)

    def apply_filters(self, qs):
        self.get_filter_values()
        qs = annotate_cliente_queryset(qs)

        if self.search_query:
            qs = qs.filter(
                Q(nombre__icontains=self.search_query)
                | Q(telefono__icontains=self.search_query)
                | Q(email__icontains=self.search_query)
                | Q(documento__icontains=self.search_query)
            )

        if self.tipo_filter == "empresa":
            qs = qs.filter(es_empresa=True)
        elif self.tipo_filter == "persona":
            qs = qs.filter(es_empresa=False)

        if self.origen_filter:
            qs = qs.filter(origen=self.origen_filter)

        if self.estado_filter == "reciente":
            qs = qs.filter(ultimo_contacto__gte=self.reciente_threshold)
        elif self.estado_filter == "sin_contacto":
            qs = qs.filter(ultimo_contacto__isnull=True)
        elif self.estado_filter == "inactivo":
            qs = qs.filter(
                Q(ultimo_contacto__lt=self.inactivo_threshold) | Q(ultimo_contacto__isnull=True)
            )
        elif self.estado_filter == "nuevos":
            qs = qs.filter(creado__gte=self.reciente_threshold)

        allowed_orders = {
            "nombre",
            "-nombre",
            "creado",
            "-creado",
            "actualizado",
            "-actualizado",
            "ultimo_contacto",
            "-ultimo_contacto",
        }
        if self.order in allowed_orders:
            qs = qs.order_by(self.order)
        else:
            qs = qs.order_by("nombre")
        return qs

    def get_summary_context(self, queryset):
        stats = queryset.aggregate(
            total=Count("id"),
            empresas=Count("id", filter=Q(es_empresa=True)),
            personas=Count("id", filter=Q(es_empresa=False)),
            total_vehiculos=Coalesce(Sum("vehiculos_count"), Value(0)),
            total_citas=Coalesce(Sum("citas_count"), Value(0)),
        )
        recientes = queryset.filter(creado__gte=self.reciente_threshold).count()
        sin_contacto = queryset.filter(ultimo_contacto__isnull=True).count()
        inactivos = queryset.filter(
            Q(ultimo_contacto__lt=self.inactivo_threshold) | Q(ultimo_contacto__isnull=True)
        ).count()

        return {
            "total": stats.get("total") or 0,
            "empresas": stats.get("empresas") or 0,
            "personas": stats.get("personas") or 0,
            "vehiculos": stats.get("total_vehiculos") or 0,
            "citas": stats.get("total_citas") or 0,
            "nuevos_mes": recientes,
            "sin_contacto": sin_contacto,
            "inactivos": inactivos,
        }


class ClienteListView(LoginRequiredMixin, ClienteFilterMixin, ListView):
    model = Cliente
    template_name = "clientes/list.html"
    context_object_name = "clientes"

    def get_queryset(self):
        qs = Cliente.objects.all()
        return self.apply_filters(qs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        params = self.request.GET.copy()
        params.pop("page", None)
        query_string = params.urlencode()

        summary = self.get_summary_context(self.object_list)

        context.update(
            {
                "search_query": self.search_query,
                "tipo_filter": self.tipo_filter,
                "origen_filter": self.origen_filter,
                "estado_filter": self.estado_filter,
                "order": self.order,
                "has_filters": any(
                    [self.search_query, self.tipo_filter, self.origen_filter, self.estado_filter, self.order]
                ),
                "origen_options": Cliente.Origen.choices,
                "estado_options": [
                    ("", "Todos"),
                    ("nuevos", "Nuevos (30 días)"),
                    ("reciente", "Contacto reciente"),
                    ("inactivo", "Inactivos"),
                    ("sin_contacto", "Sin contacto"),
                ],
                "summary": summary,
                "recent_clients": Cliente.objects.order_by("-creado")[:5],
                "follow_up_needed": Cliente.objects.filter(
                    Q(ultimo_contacto__lt=self.inactivo_threshold) | Q(ultimo_contacto__isnull=True)
                ).order_by("ultimo_contacto")[:5],
                "reciente_threshold": self.reciente_threshold,
                "inactivo_threshold": self.inactivo_threshold,
                "query_string": query_string,
            }
        )
        return context


class ClienteCreateView(LoginRequiredMixin, CreateView):
    model = Cliente
    form_class = ClienteForm
    template_name = "clientes/form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Cliente creado correctamente.")
        return response

    def get_success_url(self):
        return reverse("clientes:detail", args=[self.object.pk])


class ClienteUpdateView(LoginRequiredMixin, UpdateView):
    model = Cliente
    form_class = ClienteForm
    template_name = "clientes/form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Cliente actualizado correctamente.")
        return response

    def get_success_url(self):
        return reverse("clientes:detail", args=[self.object.pk])


class ClienteDeleteView(LoginRequiredMixin, DeleteView):
    model = Cliente
    template_name = "clientes/confirm_delete.html"
    success_url = reverse_lazy("clientes:list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Cliente eliminado.")
        return super().delete(request, *args, **kwargs)


class ClienteDetailView(LoginRequiredMixin, DetailView):
    model = Cliente
    template_name = "clientes/detail.html"
    context_object_name = "cliente"

    def get_queryset(self):
        qs = Cliente.objects.all()
        return annotate_cliente_queryset(qs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        cliente = self.object

        vehiculos = []
        citas = []
        with suppress(Exception):
            from vehiculos.models import Vehiculo  # type: ignore

            vehiculos = (
                Vehiculo.objects.select_related("cliente")
                .filter(cliente=cliente)
                .order_by("placa")[:10]
            )
        with suppress(Exception):
            from citas.models import Cita  # type: ignore

            citas = (
                Cita.objects.select_related("servicio", "vehiculo")
                .filter(cliente=cliente)
                .order_by("-fecha_inicio")[:10]
            )

        ahora = timezone.now()
        proxima_cita = None
        with suppress(Exception):
            from citas.models import Cita  # type: ignore

            proxima_cita = (
                Cita.objects.filter(cliente=cliente, fecha_inicio__gte=ahora)
                .order_by("fecha_inicio")
                .first()
            )

        if self.request.user.is_staff or self.request.user.is_superuser:
            try:
                from fidelizacion import services as loyalty

                config = loyalty.get_config()
                saldo = loyalty.obtener_saldo(cliente)
                historial_preview = list(loyalty.obtener_historial(cliente, limit=5))
                proximo = None
                niveles = config.niveles_config or {}
                if niveles:
                    actual = saldo
                    mayores = [(nombre, int(umbral)) for nombre, umbral in niveles.items() if int(umbral) > actual]
                    if mayores:
                        nombre, umbral = sorted(mayores, key=lambda item: item[1])[0]
                        proximo = {"nombre": nombre, "restantes": umbral - actual}
                ctx["cliente_loyalty"] = {
                    "saldo": saldo,
                    "historial_preview": historial_preview,
                    "proximo_nivel": proximo,
                }
            except Exception:
                ctx["cliente_loyalty"] = None

        ctx.update(
            {
                "vehiculos": vehiculos,
                "citas": citas,
                "proxima_cita": proxima_cita,
                "contacto_reciente": cliente.ultimo_contacto
                and cliente.ultimo_contacto >= timezone.now() - timedelta(days=30),
                "touch_url": reverse("clientes:touch", args=[cliente.pk]),
            }
        )
        return ctx


class ClienteExportCSVView(LoginRequiredMixin, ClienteFilterMixin, View):
    """Exporta la lista filtrada (misma búsqueda) a CSV."""

    def get(self, request, *args, **kwargs):
        qs = self.apply_filters(Cliente.objects.all()).order_by("nombre")

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="clientes.csv"'
        writer = csv.writer(response)
        writer.writerow(
            [
                "Nombre",
                "Documento",
                "Tipo",
                "Teléfono",
                "Email",
                "Dirección",
                "Origen",
                "Último contacto",
                "Vehículos",
                "Citas",
                "Creado",
            ]
        )
        for c in qs:
            writer.writerow(
                [
                    c.nombre,
                    c.documento or "",
                    c.tipo_display,
                    c.telefono or "",
                    c.email or "",
                    c.direccion or "",
                    c.get_origen_display(),
                    c.ultimo_contacto.strftime("%Y-%m-%d %H:%M") if c.ultimo_contacto else "",
                    getattr(c, "vehiculos_count", ""),
                    getattr(c, "citas_count", ""),
                    c.creado.strftime("%Y-%m-%d %H:%M"),
                ]
            )
        return response


class ClienteTouchView(LoginRequiredMixin, View):
    """Marca el último contacto del cliente como ahora."""

    def post(self, request, pk, *args, **kwargs):
        cliente = get_object_or_404(Cliente, pk=pk)
        cliente.ultimo_contacto = timezone.now()
        try:
            cliente.full_clean()
        except ValidationError:
            pass
        cliente.save(update_fields=["ultimo_contacto", "actualizado"])
        messages.success(request, "Se registró el contacto con el cliente.")
        return HttpResponseRedirect(reverse("clientes:detail", args=[cliente.pk]))
