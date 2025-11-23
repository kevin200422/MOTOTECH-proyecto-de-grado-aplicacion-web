# clientes/models.py
from __future__ import annotations
from django.db import models


class Cliente(models.Model):
    class Origen(models.TextChoices):
        REFERIDO = "referido", "Referido"
        ONLINE = "online", "Canal digital"
        VISITA = "visita", "Visita espontanea"
        CORPORATIVO = "corporativo", "Convenio corporativo"
        OTROS = "otros", "Otros"

    nombre = models.CharField("Nombre", max_length=120, db_index=True)
    documento = models.CharField("Documento", max_length=30, blank=True, null=True, unique=True)
    telefono = models.CharField("Teléfono", max_length=25, blank=True)
    email = models.EmailField("Email", blank=True)
    direccion = models.CharField("Dirección", max_length=255, blank=True)
    origen = models.CharField("Origen", max_length=20, choices=Origen.choices, default=Origen.OTROS)
    es_empresa = models.BooleanField("Es empresa", default=False)
    notas = models.TextField("Notas", blank=True)
    puntos_saldo = models.PositiveIntegerField("Puntos disponibles", default=0)
    nivel = models.CharField("Nivel fidelización", max_length=30, blank=True)
    ultimo_contacto = models.DateTimeField("Ultimo contacto", blank=True, null=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "cliente"
        verbose_name_plural = "clientes"
        ordering = ["nombre"]
        indexes = [
            models.Index(fields=["nombre"]),
            models.Index(fields=["documento"]),
            models.Index(fields=["telefono"]),
            models.Index(fields=["email"]),
            models.Index(fields=["origen"]),
            models.Index(fields=["es_empresa"]),
            models.Index(fields=["puntos_saldo"]),
        ]

    def __str__(self) -> str:
        return self.nombre

    @property
    def tipo_display(self) -> str:
        return "Empresa" if self.es_empresa else "Persona"
