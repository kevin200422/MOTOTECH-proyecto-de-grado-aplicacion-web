"""
Models for the servicios app.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import models


class Servicio(models.Model):
    """Represents a service offered by the workshop."""

    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    duracion_minutos = models.PositiveIntegerField(help_text='Duracion aproximada en minutos')
    costo = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Costo interno estimado')
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'servicio'
        verbose_name_plural = 'servicios'
        ordering = ['nombre']

    def __str__(self) -> str:
        return self.nombre

    @property
    def margen_bruto(self) -> Decimal:
        precio = self.precio or Decimal('0')
        costo = self.costo or Decimal('0')
        return precio - costo

    @property
    def margen_porcentaje(self) -> float:
        precio = self.precio or Decimal('0')
        if precio > 0:
            margen = (precio - (self.costo or Decimal('0'))) / precio * 100
            return round(float(margen), 2)
        return 0.0
