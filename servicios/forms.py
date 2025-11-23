"""
Forms for the servicios app.
"""
from __future__ import annotations

from decimal import Decimal

from django import forms

from .models import Servicio


class ServicioForm(forms.ModelForm):
    """Form to create or update a service."""

    class Meta:
        model = Servicio
        fields = ['nombre', 'descripcion', 'duracion_minutos', 'costo', 'precio', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del servicio'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'duracion_minutos': forms.NumberInput(attrs={'class': 'form-control'}),
            'costo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Costo interno'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_precio(self):
        precio = self.cleaned_data.get('precio') or Decimal('0')
        if precio < 0:
            raise forms.ValidationError("El precio no puede ser negativo.")
        return precio

    def clean_costo(self):
        costo = self.cleaned_data.get('costo') or Decimal('0')
        if costo < 0:
            raise forms.ValidationError("El costo no puede ser negativo.")
        return costo

    def clean(self):
        cleaned = super().clean()
        costo = cleaned.get('costo') or Decimal('0')
        precio = cleaned.get('precio') or Decimal('0')
        if precio and costo and costo > precio:
            self.add_error('costo', "El costo no puede superar el precio de venta.")
        return cleaned
