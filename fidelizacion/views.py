from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from clientes.models import Cliente
from fidelizacion import services as loyalty
from fidelizacion.forms import AjustePuntosForm, ConfigPuntosForm
from fidelizacion.models import ConfigPuntos


ADMIN_CHECK = lambda u: u.is_superuser or u.is_staff


@login_required
@user_passes_test(ADMIN_CHECK)
def historial_cliente(request, cliente_id: int):
    cliente = get_object_or_404(Cliente, pk=cliente_id)
    movimientos = loyalty.obtener_historial(cliente)
    paginator = Paginator(movimientos, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    contexto = {
        'cliente': cliente,
        'page_obj': page_obj,
        'saldo': loyalty.obtener_saldo(cliente),
    }
    return render(request, 'fidelizacion/historial_cliente.html', contexto)


@login_required
@user_passes_test(ADMIN_CHECK)
def ajustar_puntos(request, cliente_id: int):
    cliente = get_object_or_404(Cliente, pk=cliente_id)
    if request.method == 'POST':
        form = AjustePuntosForm(request.POST)
        if form.is_valid():
            puntos = form.cleaned_data['puntos']
            motivo = form.cleaned_data.get('motivo') or 'Ajuste manual'
            try:
                loyalty.bonificar_puntos(
                    cliente,
                    puntos,
                    referencia=f"ajuste:{cliente.pk}:{timezone.now().timestamp()}",
                    usuario_admin=request.user,
                    motivo=motivo,
                )
                messages.success(request, 'Ajuste aplicado correctamente.')
                return redirect('fidelizacion:historial_cliente', cliente_id=cliente.pk)
            except loyalty.LoyaltyError as exc:
                form.add_error(None, str(exc))
    else:
        form = AjustePuntosForm()
    contexto = {
        'cliente': cliente,
        'form': form,
        'saldo_actual': loyalty.obtener_saldo(cliente),
    }
    return render(request, 'fidelizacion/ajustar_cliente.html', contexto)


@login_required
@user_passes_test(ADMIN_CHECK)
def configuracion(request):
    config = ConfigPuntos.load()
    if request.method == 'POST':
        form = ConfigPuntosForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configuración actualizada.')
            return redirect('fidelizacion:configuracion')
    else:
        form = ConfigPuntosForm(instance=config)
    return render(request, 'fidelizacion/configuracion.html', {'form': form})
