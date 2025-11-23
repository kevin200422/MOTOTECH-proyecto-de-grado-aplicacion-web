from django.contrib import admin
from .models import ConfigPuntos, HistorialPuntos


@admin.register(ConfigPuntos)
class ConfigPuntosAdmin(admin.ModelAdmin):
    list_display = ("puntos_por_monto", "monto_base_cop", "puntos_equivalencia", "valor_redencion_cop", "actualizado")
    filter_horizontal = ("exclusiones_servicios",)

    def has_add_permission(self, request):
        # Solo permitir agregar una config si no existe.
        if ConfigPuntos.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(HistorialPuntos)
class HistorialPuntosAdmin(admin.ModelAdmin):
    list_display = ("fecha", "cliente", "tipo", "puntos_ganados", "puntos_usados", "saldo_resultante", "referencia")
    list_filter = ("tipo", "fecha")
    search_fields = ("cliente__nombre", "referencia", "motivo")
    autocomplete_fields = ("cliente", "usuario_admin")
    readonly_fields = ("fecha", "saldo_resultante")
