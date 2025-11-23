from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import (
    Avg,
    Case,
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    Q,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Greatest
from django.db.utils import OperationalError
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import MovimientoInventarioForm, RepuestoForm
from .models import CategoriaRepuesto, MovimientoInventario, Repuesto
from .utils import tabla_existe


def _annotate_metricas(queryset):
    """Annotate queryset with calculated inventory metrics."""
    return queryset.annotate(
        umbral_stock=Greatest(F("stock_seguridad"), F("stock_minimo")),
        valor_inventario_calc=ExpressionWrapper(
            F("stock") * F("costo_unitario"), output_field=DecimalField(max_digits=18, decimal_places=2)
        ),
        valor_potencial_calc=ExpressionWrapper(
            F("stock") * F("precio_venta"), output_field=DecimalField(max_digits=18, decimal_places=2)
        ),
        margen_unitario_calc=ExpressionWrapper(
            F("precio_venta") - F("costo_unitario"), output_field=DecimalField(max_digits=12, decimal_places=2)
        ),
        margen_porcentaje_calc=Case(
            When(
                precio_venta__gt=0,
                then=ExpressionWrapper(
                    (F("precio_venta") - F("costo_unitario")) * 100 / F("precio_venta"),
                    output_field=DecimalField(max_digits=7, decimal_places=2),
                ),
            ),
            default=Value(0),
            output_field=DecimalField(max_digits=7, decimal_places=2),
        ),
    )


class InventarioListView(LoginRequiredMixin, ListView):
    model = Repuesto
    template_name = "inventario/list.html"
    context_object_name = "repuestos"

    inventario_migrado: bool = True
    mensaje_bd: str = ""

    def get_queryset(self):
        if not tabla_existe("inventario_repuesto"):
            self.inventario_migrado = False
            self.mensaje_bd = (
                "No hay tablas de Inventario. Ejecuta las migraciones para crear inventario_repuesto."
            )
            return Repuesto.objects.none()

        try:
            queryset = _annotate_metricas(Repuesto.objects.all())
        except OperationalError:
            self.inventario_migrado = False
            self.mensaje_bd = (
                "No se pudo consultar la tabla inventario_repuesto. Verifica y ejecuta migraciones."
            )
            return Repuesto.objects.none()

        self.inventario_migrado = True
        self.mensaje_bd = ""

        search_query = (self.request.GET.get("q") or "").strip()
        categoria = (self.request.GET.get("categoria") or "").strip()
        estado = (self.request.GET.get("estado") or "").strip()
        order = (self.request.GET.get("o") or "").strip()

        if search_query:
            queryset = queryset.filter(
                Q(nombre__icontains=search_query)
                | Q(codigo__icontains=search_query)
                | Q(descripcion__icontains=search_query)
                | Q(proveedor__icontains=search_query)
            )

        if categoria:
            queryset = queryset.filter(categoria=categoria)

        if estado == "activos":
            queryset = queryset.filter(activo=True)
        elif estado == "inactivos":
            queryset = queryset.filter(activo=False)
        elif estado == "critico":
            queryset = queryset.filter(stock__lte=F("umbral_stock"))
        elif estado == "sin_stock":
            queryset = queryset.filter(stock=0)
        elif estado == "saturado":
            queryset = queryset.filter(stock_maximo__gt=0, stock__gte=F("stock_maximo"))

        order_map = {
            "nombre": "nombre",
            "-nombre": "-nombre",
            "codigo": "codigo",
            "-codigo": "-codigo",
            "stock": "stock",
            "-stock": "-stock",
            "precio": "precio_venta",
            "-precio": "-precio_venta",
            "costo": "costo_unitario",
            "-costo": "-costo_unitario",
            "margen": "margen_unitario_calc",
            "-margen": "-margen_unitario_calc",
            "valor": "valor_inventario_calc",
            "-valor": "-valor_inventario_calc",
        }
        return queryset.order_by(order_map.get(order, "nombre"))

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        search_query = (self.request.GET.get("q") or "").strip()
        categoria = (self.request.GET.get("categoria") or "").strip()
        estado = (self.request.GET.get("estado") or "").strip()
        order = (self.request.GET.get("o") or "").strip()

        params = self.request.GET.copy()
        params.pop("page", None)

        stats_qs = self.object_list
        stats = stats_qs.aggregate(
            total_items=Count("id"),
            total_stock=Coalesce(Sum("stock"), Value(0)),
            valor_inventario=Coalesce(
                Sum("valor_inventario_calc"),
                Value(0, output_field=DecimalField(max_digits=18, decimal_places=2)),
            ),
            valor_potencial=Coalesce(
                Sum("valor_potencial_calc"),
                Value(0, output_field=DecimalField(max_digits=18, decimal_places=2)),
            ),
            margen_promedio=Coalesce(
                Avg("margen_porcentaje_calc"),
                Value(0, output_field=DecimalField(max_digits=7, decimal_places=2)),
            ),
        )
        low_stock_count = stats_qs.filter(stock__lte=F("umbral_stock")).count()
        sin_stock_count = stats_qs.filter(stock=0).count()

        context.update(
            {
                "inventario_migrado": self.inventario_migrado,
                "mensaje_bd": self.mensaje_bd,
                "search_query": search_query,
                "categoria_filter": categoria,
                "estado_filter": estado,
                "order": order,
                "has_filters": any([search_query, categoria, estado, order]),
                "categoria_options": CategoriaRepuesto.choices,
                "estado_options": [
                    ("", "Todos"),
                    ("activos", "Activos"),
                    ("inactivos", "Inactivos"),
                    ("critico", "Criticos"),
                    ("sin_stock", "Sin stock"),
                    ("saturado", "Saturados"),
                ],
                "summary": {
                    "items": stats["total_items"] or 0,
                    "stock_total": stats["total_stock"] or 0,
                    "valor_inventario": stats["valor_inventario"] or Decimal("0"),
                    "valor_potencial": stats["valor_potencial"] or Decimal("0"),
                    "margen_promedio": stats["margen_promedio"] or Decimal("0"),
                    "criticos": low_stock_count,
                    "sin_stock": sin_stock_count,
                },
                "query_string": params.urlencode(),
            }
        )
        return context


class InventarioDetailView(LoginRequiredMixin, DetailView):
    model = Repuesto
    template_name = "inventario/detail.html"
    context_object_name = "repuesto"

    def get_queryset(self):
        return _annotate_metricas(
            Repuesto.objects.select_related().prefetch_related("movimientos", "movimientos__realizado_por")
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        movimientos_qs = self.object.movimientos.select_related("realizado_por").all()
        entradas_qs = list(movimientos_qs.filter(tipo=MovimientoInventario.Tipo.ENTRADA))
        salidas_qs = list(movimientos_qs.filter(tipo=MovimientoInventario.Tipo.SALIDA))

        def _valor_acumulado(items):
            total = Decimal("0")
            for mov in items:
                costo = mov.costo_unitario or self.object.costo_unitario or Decimal("0")
                total += Decimal(mov.cantidad) * costo
            return total

        context.update(
            {
                "movimientos": movimientos_qs[:12],
                "estadisticas_movimientos": {
                    "entradas": sum(m.cantidad for m in entradas_qs),
                    "salidas": sum(m.cantidad for m in salidas_qs),
                    "valor_entradas": _valor_acumulado(entradas_qs),
                    "valor_salidas": _valor_acumulado(salidas_qs),
                },
            }
        )
        return context


class InventarioCreateView(LoginRequiredMixin, CreateView):
    model = Repuesto
    form_class = RepuestoForm
    template_name = "inventario/form.html"

    def form_valid(self, form: RepuestoForm):
        messages.success(self.request, "Repuesto creado correctamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("inventario:detail", args=[self.object.pk])


class InventarioUpdateView(LoginRequiredMixin, UpdateView):
    model = Repuesto
    form_class = RepuestoForm
    template_name = "inventario/form.html"

    def form_valid(self, form: RepuestoForm):
        messages.success(self.request, "Repuesto actualizado correctamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("inventario:detail", args=[self.object.pk])


class InventarioDeleteView(LoginRequiredMixin, DeleteView):
    model = Repuesto
    template_name = "inventario/confirm_delete.html"
    success_url = reverse_lazy("inventario:list")
    context_object_name = "repuesto"

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Repuesto eliminado del inventario.")
        return super().delete(request, *args, **kwargs)


class MovimientoInventarioCreateView(LoginRequiredMixin, CreateView):
    model = MovimientoInventario
    form_class = MovimientoInventarioForm
    template_name = "inventario/movement_form.html"

    repuesto: Repuesto | None = None

    def dispatch(self, request, *args, **kwargs):
        self.repuesto = get_object_or_404(Repuesto, pk=kwargs.get("pk"))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["repuesto"] = self.repuesto
        return kwargs

    def form_valid(self, form: MovimientoInventarioForm):
        movimiento: MovimientoInventario = form.save(commit=False)
        movimiento.repuesto = self.repuesto
        movimiento.realizado_por = self.request.user if self.request.user.is_authenticated else None
        try:
            movimiento.save()
        except ValidationError as exc:
            form.add_error(None, exc)
            return self.form_invalid(form)
        messages.success(
            self.request,
            f"Movimiento registrado. Stock actual: {movimiento.repuesto.stock} {movimiento.repuesto.unidad_medida}.",
        )
        self.object = movimiento
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("inventario:detail", args=[self.repuesto.pk])

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["repuesto"] = self.repuesto
        context["movimientos_recientes"] = self.repuesto.movimientos.select_related("realizado_por")[:6]
        return context
