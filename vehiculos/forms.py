"""
Forms for creating and updating vehicles.
"""
from __future__ import annotations

from django import forms

from .models import Vehiculo


class VehiculoForm(forms.ModelForm):
    """Form for the Vehiculo model."""

    class Meta:
        model = Vehiculo
        fields = ['cliente', 'marca', 'modelo', 'anio', 'placa', 'color']
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'marca': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Marca del vehiculo'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Modelo / version'}),
            'anio': forms.NumberInput(attrs={'class': 'form-control', 'min': 1900, 'max': 2100, 'placeholder': '2024'}),
            'placa': forms.TextInput(attrs={'class': 'form-control text-uppercase', 'placeholder': 'Ej: ABC123'}),
            'color': forms.TextInput(attrs={'class': 'form-control text-capitalize', 'placeholder': 'Color principal'}),
        }

    def clean_placa(self) -> str:
        placa = (self.cleaned_data.get("placa") or "").strip().upper()
        return placa

    def clean_color(self) -> str:
        color = (self.cleaned_data.get("color") or "").strip()
        if color:
            color = color.capitalize()
        return color
