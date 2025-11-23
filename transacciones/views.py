"""Views for the transacciones app."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.shortcuts import redirect, render

from fidelizacion import services as loyalty
from fidelizacion.models import HistorialPuntos
from .forms import TransaccionForm
from .models import Transaccion


ADMIN_CHECK = lambda u: u.is_superuser or u.is_staff


@login_required
@user_passes_test(ADMIN_CHECK)
def lista_transacciones(request):
    transacciones = (
        Transaccion.objects.select_related("cita", "cita__cliente", "cita__servicio")
        .order_by("-fecha")
    )
    return render(request, "transacciones/list.html", {"transacciones": transacciones})


@login_required
@user_passes_test(ADMIN_CHECK)
def crear_transaccion(request):
    context = {"title": "Nueva transaccion"}
    config = loyalty.get_config()
    if request.method == "POST":
        form = TransaccionForm(request.POST, request=request)
        if form.is_valid():
            cliente = form.get_cliente()
            if cliente is None:
                form.add_error(None, "No se pudo identificar el cliente asociado a la cita seleccionada.")
            else:
                try:
                    with transaction.atomic():
                        transaccion = form.save(commit=False)
                        transaccion.save()
                        puntos_a_canjear = form.cleaned_data.get("puntos_a_canjear") or 0
                        referencia_base = transaccion.referencia_fidelizacion
                        if puntos_a_canjear:
                            valor_descuento = loyalty.canjear_puntos(
                                cliente,
                                puntos_a_canjear,
                                referencia=f"{referencia_base}:canje",
                                usuario_admin=request.user,
                                motivo="Canje aplicado en facturacion",
                            )
                            transaccion.descuento_puntos = valor_descuento
                            transaccion.puntos_redimidos = puntos_a_canjear
                            transaccion.monto = max(transaccion.monto - valor_descuento, Decimal("0.00"))

                        cita = transaccion.cita
                        if (
                            cita.estado == "completada"
                            and not HistorialPuntos.objects.filter(
                                cliente=cliente,
                                referencia=f"{referencia_base}:gana",
                                tipo=HistorialPuntos.Tipo.GANA,
                            ).exists()
                        ):
                            puntos_otorgados = loyalty.otorgar_puntos(
                                cliente,
                                transaccion.subtotal,
                                referencia=f"{referencia_base}:gana",
                                usuario_admin=request.user,
                                motivo=f"Servicio {cita.servicio.nombre}" if getattr(cita, "servicio", None) else "",
                                servicio=getattr(cita, "servicio", None),
                            )
                            transaccion.puntos_otorgados = puntos_otorgados > 0

                        transaccion.save()
                    messages.success(request, "Transaccion registrada correctamente.")
                    return redirect("transacciones:list")
                except loyalty.LoyaltyError as exc:
                    form.add_error(None, str(exc))
    else:
        form = TransaccionForm(request=request)

    context["form"] = form
    context["config_puntos"] = config
    cliente_form = form.get_cliente()
    if cliente_form:
        context["cliente_loyalty"] = {
            "cliente": cliente_form,
            "saldo": loyalty.obtener_saldo(cliente_form),
            "equivalencia_valor": config.valor_redencion_cop,
            "equivalencia_puntos": config.puntos_equivalencia,
        }
        raw_subtotal = None
        if request.method == "POST":
            raw_subtotal = request.POST.get("subtotal")
        elif form.initial.get("subtotal") is not None:
            raw_subtotal = form.initial.get("subtotal")
        elif getattr(form.instance, "subtotal", None):
            raw_subtotal = form.instance.subtotal

        preview = None
        if raw_subtotal not in (None, "", "0"):
            try:
                subtotal_preview = Decimal(str(raw_subtotal))
            except (InvalidOperation, ValueError):
                subtotal_preview = None
            if subtotal_preview is not None and subtotal_preview > 0:
                preview = loyalty.calcular_puntos_detallado(
                    subtotal_preview,
                    cliente=cliente_form,
                    config=config,
                )
        context["calculo_puntos_preview"] = preview
    else:
        context["calculo_puntos_preview"] = None
    return render(request, "transacciones/form.html", context)
