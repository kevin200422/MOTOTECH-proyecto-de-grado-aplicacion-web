"""
Forms for managing inventory items.
"""
from __future__ import annotations

from django import forms

from .models import MovimientoInventario, Repuesto


class RepuestoForm(forms.ModelForm):
    """Form to create or update a spare part."""

    class Meta:
        model = Repuesto
        fields = [
            'nombre',
            'descripcion',
            'codigo',
            'categoria',
            'unidad_medida',
            'proveedor',
            'ubicacion',
            'stock',
            'stock_seguridad',
            'stock_minimo',
            'stock_maximo',
            'costo_unitario',
            'precio_venta',
            'tiempo_reposicion_dias',
            'activo',
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del repuesto'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'codigo': forms.TextInput(attrs={'class': 'form-control text-uppercase', 'placeholder': 'Codigo interno'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'unidad_medida': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Unidad (ej: unidad, litro, kit)'}),
            'proveedor': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Proveedor habitual'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ubicacion en bodega'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'stock_seguridad': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'stock_minimo': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'stock_maximo': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'costo_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
            'precio_venta': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
            'tiempo_reposicion_dias': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_precio_venta(self):
        precio = self.cleaned_data.get('precio_venta') or 0
        if precio < 0:
            raise forms.ValidationError("El precio de venta no puede ser negativo.")
        return precio

    def clean_costo_unitario(self):
        costo = self.cleaned_data.get('costo_unitario') or 0
        if costo < 0:
            raise forms.ValidationError("El costo unitario no puede ser negativo.")
        return costo

    def clean(self):
        cleaned = super().clean()
        costo = cleaned.get('costo_unitario') or 0
        precio = cleaned.get('precio_venta') or 0
        stock = cleaned.get('stock') or 0
        stock_max = cleaned.get('stock_maximo') or 0

        if precio and costo and costo > precio:
            self.add_error('costo_unitario', "El costo no puede superar al precio de venta.")
        if stock_max and stock > stock_max:
            self.add_error('stock_maximo', "El stock maximo debe ser mayor o igual al stock actual.")
        return cleaned


class MovimientoInventarioForm(forms.ModelForm):
    """Formulario para registrar entradas y salidas de inventario."""

    class Meta:
        model = MovimientoInventario
        fields = ['tipo', 'cantidad', 'costo_unitario', 'referencia', 'notas']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'costo_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
            'referencia': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Factura, orden, etc.'}),
            'notas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Notas adicionales'}),
        }

    def __init__(self, *args, repuesto: Repuesto | None = None, **kwargs):
        self.repuesto = repuesto
        super().__init__(*args, **kwargs)
        if repuesto and not self.initial.get('costo_unitario'):
            self.fields['costo_unitario'].initial = repuesto.costo_unitario

    def clean_costo_unitario(self):
        costo = self.cleaned_data.get('costo_unitario')
        if costo is not None and costo < 0:
            raise forms.ValidationError("El costo no puede ser negativo.")
        return costo

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get('cantidad') or 0
        if cantidad <= 0:
            raise forms.ValidationError("La cantidad debe ser mayor a cero.")
        return cantidad
