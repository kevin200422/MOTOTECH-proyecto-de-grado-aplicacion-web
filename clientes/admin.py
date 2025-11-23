from django.contrib import admin
from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "documento", "telefono", "email", "origen", "puntos_saldo", "nivel", "creado")
    search_fields = ("nombre", "documento", "telefono", "email")
    list_filter = ("origen", "es_empresa", "nivel")
    readonly_fields = ("puntos_saldo", "nivel", "creado", "actualizado")
    fieldsets = (
        ("Identificación", {"fields": ("nombre", "documento", "es_empresa", "nivel")}),
        ("Contacto", {"fields": ("telefono", "email", "direccion")}),
        ("Origen y notas", {"fields": ("origen", "notas")}),
        ("Fidelización", {"fields": ("puntos_saldo",)}),
        ("Timestamps", {"classes": ("collapse",), "fields": ("creado", "actualizado")}),
    )

    def get_readonly_fields(self, request, obj=None):
        ro = list(self.readonly_fields)
        if not request.user.is_superuser:
            ro += ["nivel"]
        return ro
