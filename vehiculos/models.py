"""
Database models for the vehiculos app.

This module defines the Vehiculo model, which is associated with a
Cliente and stores basic information about a vehicle.
"""
from __future__ import annotations

from django.db import models


class Vehiculo(models.Model):
    """Represents a vehicle associated to a client."""

    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.CASCADE, related_name='vehiculos')
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    anio = models.PositiveIntegerField(verbose_name='Año')
    placa = models.CharField(max_length=10, unique=True)
    color = models.CharField(max_length=30, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'vehículo'
        verbose_name_plural = 'vehículos'
        ordering = ['placa']

    def __str__(self) -> str:
        return f"{self.placa} ({self.marca} {self.modelo})"