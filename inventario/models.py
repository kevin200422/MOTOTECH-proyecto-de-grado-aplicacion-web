from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction


class CategoriaRepuesto(models.TextChoices):
    MECANICA = "mecanica", "Mecanica"
    ELECTRICA = "electrica", "Electrica"
    MOTOR = "motor", "Motor"
    CARROCERIA = "carroceria", "Carroceria"
    OTROS = "otros", "Otros"


class Repuesto(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    categoria = models.CharField(max_length=30, choices=CategoriaRepuesto.choices, default=CategoriaRepuesto.MECANICA)
    unidad_medida = models.CharField(max_length=20, default="unidad")
    proveedor = models.CharField(max_length=150, blank=True)
    ubicacion = models.CharField(max_length=100, blank=True, help_text="Ubicacion fisica, ej: Rack A-01")
    stock = models.PositiveIntegerField(default=0)
    stock_seguridad = models.PositiveIntegerField(default=0, help_text="Nivel minimo recomendado")
    stock_minimo = models.PositiveIntegerField(default=0)
    stock_maximo = models.PositiveIntegerField(default=0, help_text="Capacidad maxima planificada")
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    precio_venta = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tiempo_reposicion_dias = models.PositiveIntegerField(default=0, help_text="Dias estimados para reposicion")
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Repuesto"
        verbose_name_plural = "Repuestos"

    def __str__(self) -> str:
        return f"{self.codigo} - {self.nombre}"

    @property
    def bajo_stock(self) -> bool:
        try:
            umbral = max(self.stock_seguridad, self.stock_minimo)
            return bool(umbral) and self.stock <= umbral
        except Exception:
            return False

    @property
    def stock_disponible(self) -> int:
        return max(self.stock - self.stock_seguridad, 0)

    @property
    def capacidad_restante(self) -> int:
        if self.stock_maximo:
            return max(self.stock_maximo - self.stock, 0)
        return 0

    @property
    def valor_inventario(self) -> Decimal:
        return (self.costo_unitario or Decimal("0")) * Decimal(self.stock or 0)

    @property
    def valor_potencial(self) -> Decimal:
        return (self.precio_venta or Decimal("0")) * Decimal(self.stock or 0)

    @property
    def margen_unitario(self) -> Decimal:
        return (self.precio_venta or Decimal("0")) - (self.costo_unitario or Decimal("0"))

    @property
    def margen_porcentaje(self) -> float:
        precio = self.precio_venta or Decimal("0")
        if precio > 0:
            margen = (precio - (self.costo_unitario or Decimal("0"))) / precio * 100
            return round(float(margen), 2)
        return 0.0

    @property
    def estado_stock(self) -> str:
        if self.stock == 0:
            return "sin_stock"
        if self.bajo_stock:
            return "critico"
        if self.stock_maximo and self.stock >= self.stock_maximo:
            return "saturado"
        return "ok"


class MovimientoInventario(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = "entrada", "Entrada"
        SALIDA = "salida", "Salida"

    repuesto = models.ForeignKey(Repuesto, on_delete=models.PROTECT, related_name="movimientos")
    tipo = models.CharField(max_length=15, choices=Tipo.choices)
    cantidad = models.PositiveIntegerField()
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    referencia = models.CharField(max_length=120, blank=True)
    notas = models.TextField(blank=True)
    realizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_inventario",
    )
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "Movimiento de inventario"
        verbose_name_plural = "Movimientos de inventario"

    def __str__(self) -> str:
        direccion = "Entrada" if self.tipo == self.Tipo.ENTRADA else "Salida"
        return f"{direccion} {self.cantidad} {self.repuesto.unidad_medida} - {self.repuesto.nombre}"

    @property
    def valor_total(self) -> Decimal:
        costo = self.costo_unitario or self.repuesto.costo_unitario or Decimal("0")
        return Decimal(self.cantidad) * costo

    def clean(self):
        super().clean()
        if self.cantidad <= 0:
            raise ValidationError({"cantidad": "La cantidad debe ser mayor a cero."})
        if self.repuesto_id and self.tipo == self.Tipo.SALIDA:
            disponible = Repuesto.objects.filter(pk=self.repuesto_id).values_list("stock", flat=True).first() or 0
            if self.cantidad > disponible:
                raise ValidationError({"cantidad": "No hay stock suficiente para realizar la salida solicitada."})

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Los movimientos existentes no pueden modificarse.")

        self.full_clean()

        with transaction.atomic():
            repuesto = Repuesto.objects.select_for_update().get(pk=self.repuesto_id)

            if self.tipo == self.Tipo.SALIDA and self.cantidad > repuesto.stock:
                raise ValidationError({"cantidad": "No hay stock suficiente para realizar la salida solicitada."})

            super().save(*args, **kwargs)

            if self.tipo == self.Tipo.ENTRADA:
                repuesto.stock = repuesto.stock + self.cantidad
                if self.costo_unitario is not None:
                    repuesto.costo_unitario = self.costo_unitario
            else:
                repuesto.stock = max(repuesto.stock - self.cantidad, 0)

            repuesto.save(update_fields=["stock", "costo_unitario", "actualizado"])
