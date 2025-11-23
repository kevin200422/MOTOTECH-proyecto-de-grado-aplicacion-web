from django.db import models
from django.utils import timezone
from clientes.models import Cliente
from vehiculos.models import Vehiculo
from servicios.models import Servicio

class Cita(models.Model):
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("confirmada", "Confirmada"),
        ("en_proceso", "En proceso"),
        ("completada", "Completada"),
        ("cancelada", "Cancelada"),
        ("no_show", "No asistió"),
    ]

    titulo = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True)
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")

    cliente = models.ForeignKey(
        Cliente, on_delete=models.PROTECT, related_name="citas"
    )
    vehiculo = models.ForeignKey(
        Vehiculo, on_delete=models.PROTECT, related_name="citas"
    )
    servicio = models.ForeignKey(
        Servicio, on_delete=models.PROTECT, related_name="citas"
    )

    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_inicio"]
        indexes = [
            models.Index(fields=["fecha_inicio"]),
            models.Index(fields=["estado"]),
        ]

    def __str__(self):
        return f"{self.titulo} - {self.cliente} ({self.fecha_inicio:%Y-%m-%d %H:%M})"

    @property
    def duracion_min(self):
        return int((self.fecha_fin - self.fecha_inicio).total_seconds() // 60)

    def es_futura(self):
        return self.fecha_inicio >= timezone.now()
