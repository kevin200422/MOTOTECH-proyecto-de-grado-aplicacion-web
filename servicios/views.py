"""Class-based views for the servicios app."""
from __future__ import annotations

from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import ServicioForm
from .models import Servicio


class StaffOrAdminRequiredMixin(UserPassesTestMixin):
    """Allow access only to staff members or superusers."""

    permission_denied_message = "Solo el personal autorizado puede gestionar servicios."

    def test_func(self) -> bool:
        user = self.request.user
        return bool(user and (user.is_superuser or user.is_staff))


class ServicioListView(LoginRequiredMixin, ListView):
    """List the services available in the workshop."""

    model = Servicio
    template_name = "servicios/list.html"
    context_object_name = "servicios"
    paginate_by = 20

    def get_queryset(self):
        queryset = Servicio.objects.annotate(
            citas_count=Count("citas", distinct=True),
            margen=ExpressionWrapper(
                F("precio") - F("costo"),
                output_field=DecimalField(max_digits=10, decimal_places=2),
            ),
        )

        estado = (self.request.GET.get("estado") or "").strip().lower()
        if estado == "activos":
            queryset = queryset.filter(activo=True)
        elif estado == "inactivos":
            queryset = queryset.filter(activo=False)

        search = (self.request.GET.get("q") or "").strip()
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) | Q(descripcion__icontains=search)
            )

        order = (self.request.GET.get("o") or "").strip()
        allowed_orders = {
            "nombre",
            "-nombre",
            "precio",
            "-precio",
            "duracion_minutos",
            "-duracion_minutos",
            "creado",
            "-creado",
            "costo",
            "-costo",
            "margen",
            "-margen",
        }
        queryset = queryset.order_by(order if order in allowed_orders else "nombre")
        return queryset

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        search_query = (self.request.GET.get("q") or "").strip()
        estado = (self.request.GET.get("estado") or "").strip().lower()
        order = (self.request.GET.get("o") or "").strip()

        params = self.request.GET.copy()
        params.pop("page", None)

        context["title"] = "Servicios"
        context["search_query"] = search_query
        context["estado_filter"] = estado
        context["order"] = order
        context["has_filters"] = any([search_query, estado, order])
        context["query_string"] = params.urlencode()
        context["estado_options"] = [
            ("", "Todos"),
            ("activos", "Activos"),
            ("inactivos", "Inactivos"),
        ]

        summary_all = Servicio.objects.aggregate(
            total=Count("id"),
            activos=Count("id", filter=Q(activo=True)),
            inactivos=Count("id", filter=Q(activo=False)),
            ingreso_total=Sum("precio"),
            costo_total=Sum("costo"),
        )
        summary_filtered = self.object_list.aggregate(
            ingreso_total=Sum("precio"),
            costo_total=Sum("costo"),
        )

        ingreso_filtrado = summary_filtered["ingreso_total"] or 0
        costo_filtrado = summary_filtered["costo_total"] or 0
        margen_filtrado = ingreso_filtrado - costo_filtrado

        context["summary"] = {
            "total": summary_all["total"] or 0,
            "activos": summary_all["activos"] or 0,
            "inactivos": summary_all["inactivos"] or 0,
            "ingreso_estimado": ingreso_filtrado,
            "margen_estimado": margen_filtrado,
        }
        context["recent_servicios"] = (
            Servicio.objects.order_by("-actualizado")[:5]
        )
        context["top_servicios"] = (
            Servicio.objects.annotate(
                margen=ExpressionWrapper(
                    F("precio") - F("costo"),
                    output_field=DecimalField(max_digits=10, decimal_places=2),
                )
            )
            .filter(activo=True)
            .order_by("-margen")[:5]
        )
        return context


class ServicioDetailView(LoginRequiredMixin, DetailView):
    """Display the details of a single service."""

    model = Servicio
    template_name = "servicios/detail.html"
    context_object_name = "servicio"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = self.object.nombre
        context["margen_porcentaje"] = self.object.margen_porcentaje
        context["citas_recientes"] = (
            self.object.citas.select_related("cliente", "vehiculo")
            .order_by("-fecha_inicio")[:6]
        )
        context["clientes_frecuentes"] = (
            self.object.citas.values("cliente__id", "cliente__nombre")
            .annotate(total=Count("id"))
            .order_by("-total")[:5]
        )
        return context


class ServicioCreateView(StaffOrAdminRequiredMixin, LoginRequiredMixin, CreateView):
    """Create a new service record."""

    model = Servicio
    form_class = ServicioForm
    template_name = "servicios/form.html"
    success_url = reverse_lazy("servicios:list")
    extra_context = {"title": "Nuevo servicio"}

    def form_valid(self, form: ServicioForm):
        response = super().form_valid(form)
        messages.success(self.request, "Servicio creado correctamente.")
        return response


class ServicioUpdateView(StaffOrAdminRequiredMixin, LoginRequiredMixin, UpdateView):
    """Update an existing service."""

    model = Servicio
    form_class = ServicioForm
    template_name = "servicios/form.html"
    success_url = reverse_lazy("servicios:list")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = f"Editar servicio {self.object.nombre}"
        return context

    def form_valid(self, form: ServicioForm):
        response = super().form_valid(form)
        messages.success(self.request, "Servicio actualizado correctamente.")
        return response


class ServicioDeleteView(StaffOrAdminRequiredMixin, LoginRequiredMixin, DeleteView):
    """Delete a service."""

    model = Servicio
    template_name = "servicios/confirm_delete.html"
    success_url = reverse_lazy("servicios:list")
    context_object_name = "servicio"

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Servicio eliminado correctamente.")
        return super().delete(request, *args, **kwargs)
