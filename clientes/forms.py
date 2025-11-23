# clientes/forms.py
from __future__ import annotations
from django import forms
from django.core.exceptions import ValidationError

from .models import Cliente
import re

PHONE_RE = re.compile(r"^[\d\s\-\+\(\)]{6,}$")
DOC_RE = re.compile(r"^[\w\-\.\s]{4,}$")


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            "nombre",
            "documento",
            "es_empresa",
            "origen",
            "telefono",
            "email",
            "direccion",
            "ultimo_contacto",
            "notas",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre completo o razón social"}),
            "documento": forms.TextInput(attrs={"class": "form-control text-uppercase", "placeholder": "Documento / NIT"}),
            "es_empresa": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "origen": forms.Select(attrs={"class": "form-select"}),
            "telefono": forms.TextInput(attrs={"class": "form-control", "placeholder": "+57 300 123 4567"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "cliente@email.com"}),
            "direccion": forms.TextInput(attrs={"class": "form-control", "placeholder": "Calle 1 # 2-34, Ciudad"}),
            "ultimo_contacto": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "notas": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Notas internas, preferencias o recordatorios"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.ultimo_contacto:
            self.initial["ultimo_contacto"] = self.instance.ultimo_contacto.strftime("%Y-%m-%dT%H:%M")

    def clean_documento(self):
        documento = (self.cleaned_data.get("documento") or "").strip().upper()
        if documento and not DOC_RE.match(documento):
            raise ValidationError("Documento inválido. Usa letras, números o guiones.")
        return documento or None

    def clean_telefono(self):
        tel = (self.cleaned_data.get("telefono") or "").strip()
        if tel and not PHONE_RE.match(tel):
            raise ValidationError("Formato de teléfono no válido.")
        return tel

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        return email
