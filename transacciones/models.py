"""
Models for the transacciones app.
"""
from __future__ import annotations

from django.db import models


class Transaccion(models.Model):
    """Represents a payment transaction for a completed service."""

    METODO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta'),
        ('transferencia', 'Transferencia'),
    ]

    cita = models.ForeignKey('citas.Cita', on_delete=models.CASCADE, related_name='transacciones')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, help_text="Subtotal antes de descuentos.")
    monto = models.DecimalField(max_digits=10, decimal_places=2, help_text="Monto pagado final.")
    descuento_puntos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    puntos_redimidos = models.PositiveIntegerField(default=0)
    puntos_otorgados = models.BooleanField(default=False)
    metodo_pago = models.CharField(max_length=20, choices=METODO_CHOICES)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'transacción'
        verbose_name_plural = 'transacciones'
        ordering = ['-fecha']

    def __str__(self) -> str:
        return f"Transacción #{self.id} - {self.monto}"

    @property
    def referencia_fidelizacion(self) -> str:
        return f"transaccion:{self.pk}"
