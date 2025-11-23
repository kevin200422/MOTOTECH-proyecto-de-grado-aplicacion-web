"""Core data models for the loyalty system."""
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class ConfigPuntos(models.Model):
    """Singleton-style configuration for the loyalty program."""

    puntos_por_monto = models.PositiveIntegerField(
        default=1,
        help_text="Cantidad de puntos otorgados cuando el subtotal alcanza el monto_base_cop.",
    )
    monto_base_cop = models.PositiveIntegerField(
        default=1000,
        help_text="Monto en COP requerido para otorgar puntos (antes de impuestos/propinas).",
    )
    puntos_equivalencia = models.PositiveIntegerField(
        default=100,
        help_text="Cantidad de puntos requeridos para redimir valor_redencion_cop pesos.",
    )
    valor_redencion_cop = models.PositiveIntegerField(
        default=1000,
        help_text="Valor en COP descontado cuando se redimen puntos_equivalencia puntos.",
    )
    puntos_max_por_factura = models.PositiveIntegerField(
        default=0,
        help_text="Tope de puntos otorgados por factura (0 = sin tope).",
    )
    exclusiones_servicios = models.ManyToManyField(
        "servicios.Servicio",
        blank=True,
        related_name="excluido_fidelizacion",
        help_text="Servicios que no generan puntos.",
    )
    exclusiones_categorias = models.JSONField(
        default=list,
        blank=True,
        help_text="Lista de categorías (texto) excluidas del programa.",
    )
    niveles_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Configuración opcional de niveles {'Bronce': 0, 'Plata': 5000, ...}.",
    )
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "configuración de puntos"
        verbose_name_plural = "configuraciones de puntos"

    def save(self, *args, **kwargs):
        if not self.pk and ConfigPuntos.objects.exists():
            raise ValidationError("Ya existe una configuración de puntos. Edite la existente.")
        return super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "ConfigPuntos":
        """Return the singleton configuration, creating it when missing."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def puntos_por_monto_decimal(self) -> Decimal:
        return Decimal(self.puntos_por_monto) / Decimal(self.monto_base_cop or 1)

    def puntos_to_cop(self, puntos: int) -> Decimal:
        if puntos <= 0:
            return Decimal("0")
        factor = Decimal(self.valor_redencion_cop) / Decimal(self.puntos_equivalencia or 1)
        return (Decimal(puntos) * factor).quantize(Decimal("1.00"))


class HistorialPuntos(models.Model):
    """Audit trail for every loyalty movement per client."""

    class Tipo(models.TextChoices):
        GANA = "gana", "Gana puntos"
        USA = "usa", "Usa puntos"
        BONO = "bono", "Bonificación"
        AJUSTE = "ajuste", "Ajuste manual"
        REVERSA = "reversa", "Reversión"

    cliente = models.ForeignKey(
        "clientes.Cliente",
        on_delete=models.CASCADE,
        related_name="movimientos_puntos",
    )
    fecha = models.DateTimeField(default=timezone.now, db_index=True)
    tipo = models.CharField(max_length=12, choices=Tipo.choices)
    monto_pesos = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    puntos_ganados = models.IntegerField(default=0)
    puntos_usados = models.IntegerField(default=0)
    saldo_resultante = models.PositiveIntegerField()
    referencia = models.CharField(max_length=120, blank=True)
    usuario_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="historial_puntos_admin",
    )
    motivo = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "movimiento de puntos"
        verbose_name_plural = "movimientos de puntos"
        ordering = ["-fecha"]
        indexes = [
            models.Index(fields=["cliente", "fecha"], name="historial_cliente_fecha_idx"),
            models.Index(fields=["referencia"], name="historial_referencia_idx"),
            models.Index(fields=["tipo"], name="historial_tipo_idx"),
        ]

    def clean(self):
        if self.puntos_ganados < 0 or self.puntos_usados < 0:
            raise ValidationError("Los puntos ganados/usados deben ser positivos.")
        if self.puntos_ganados and self.puntos_usados:
            raise ValidationError("Un movimiento no puede ganar y usar puntos simultáneamente.")

    def __str__(self) -> str:
        return f"{self.get_tipo_display()} · {self.cliente} · {self.fecha:%Y-%m-%d}"
