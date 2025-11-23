"""Class-based views for the vehiculos app."""
from __future__ import annotations

from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from clientes.models import Cliente

from .forms import VehiculoForm
from .models import Vehiculo


class StaffOrAdminRequiredMixin(UserPassesTestMixin):
    """Restrict access to staff members or superusers."""

    permission_denied_message = "Solo el personal autorizado puede gestionar vehiculos."

    def test_func(self) -> bool:
        user = self.request.user
        return bool(user and (user.is_superuser or user.is_staff))


class VehiculoListView(LoginRequiredMixin, ListView):
    """List the vehicles in the system, optionally filtered by querystring."""

    model = Vehiculo
    template_name = "vehiculos/list.html"
    context_object_name = "vehiculos"
    paginate_by = 20

    def get_queryset(self):
        queryset = (
            Vehiculo.objects.select_related("cliente")
            .annotate(citas_count=Count("citas"))
        )

        cliente_id = (self.request.GET.get("cliente") or "").strip()
        if cliente_id.isdigit():
            queryset = queryset.filter(cliente_id=cliente_id)

        search = (self.request.GET.get("q") or "").strip()
        if search:
            queryset = queryset.filter(
                Q(placa__icontains=search)
                | Q(marca__icontains=search)
                | Q(modelo__icontains=search)
                | Q(cliente__nombre__icontains=search)
            )

        order = (self.request.GET.get("o") or "").strip()
        allowed_orders = {
            "placa",
            "-placa",
            "marca",
            "-marca",
            "modelo",
            "-modelo",
            "anio",
            "-anio",
            "creado",
            "-creado",
        }
        queryset = queryset.order_by(order if order in allowed_orders else "placa")
        return queryset

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        search_query = (self.request.GET.get("q") or "").strip()
        cliente_filter = (self.request.GET.get("cliente") or "").strip()
        order = (self.request.GET.get("o") or "").strip()

        context["title"] = "Vehiculos"
        context["search_query"] = search_query
        context["cliente_filter"] = cliente_filter
        context["order"] = order
        context["has_filters"] = any([search_query, cliente_filter, order])
        context["clientes_options"] = Cliente.objects.order_by("nombre").values("id", "nombre")
        params = self.request.GET.copy()
        params.pop("page", None)
        context["query_string"] = params.urlencode()
        context["summary"] = {
            "filtered": self.object_list.count(),
            "total": Vehiculo.objects.count(),
            "con_agenda": Vehiculo.objects.filter(
                citas__estado__in=["pendiente", "confirmada", "en_proceso"]
            )
            .distinct()
            .count(),
        }
        context["recent_vehiculos"] = (
            Vehiculo.objects.select_related("cliente")
            .order_by("-actualizado")[:5]
        )
        return context


class VehiculoDetailView(LoginRequiredMixin, DetailView):
    """Display details for a single vehicle."""

    model = Vehiculo
    template_name = "vehiculos/detail.html"
    context_object_name = "vehiculo"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = f"Vehiculo {self.object.placa}"
        context["citas_recientes"] = (
            self.object.citas.select_related("servicio", "cliente")
            .order_by("-fecha_inicio")[:5]
        )
        context["otros_vehiculos_cliente"] = (
            self.object.cliente.vehiculos.exclude(pk=self.object.pk)
            .order_by("placa")[:4]
            if self.object.cliente_id
            else []
        )
        return context


class VehiculoCreateView(StaffOrAdminRequiredMixin, LoginRequiredMixin, CreateView):
    """Create a new vehicle entry."""

    model = Vehiculo
    form_class = VehiculoForm
    template_name = "vehiculos/form.html"
    success_url = reverse_lazy("vehiculos:list")
    extra_context = {"title": "Nuevo vehiculo"}

    def form_valid(self, form: VehiculoForm):
        response = super().form_valid(form)
        messages.success(self.request, "Vehiculo creado correctamente.")
        return response


class VehiculoUpdateView(StaffOrAdminRequiredMixin, LoginRequiredMixin, UpdateView):
    """Update an existing vehicle entry."""

    model = Vehiculo
    form_class = VehiculoForm
    template_name = "vehiculos/form.html"
    success_url = reverse_lazy("vehiculos:list")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["title"] = f"Editar vehiculo {self.object.placa}"
        return context

    def form_valid(self, form: VehiculoForm):
        response = super().form_valid(form)
        messages.success(self.request, "Vehiculo actualizado correctamente.")
        return response


class VehiculoDeleteView(StaffOrAdminRequiredMixin, LoginRequiredMixin, DeleteView):
    """Delete a vehicle entry."""

    model = Vehiculo
    template_name = "vehiculos/confirm_delete.html"
    success_url = reverse_lazy("vehiculos:list")
    context_object_name = "vehiculo"

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Vehiculo eliminado correctamente.")
        return super().delete(request, *args, **kwargs)
