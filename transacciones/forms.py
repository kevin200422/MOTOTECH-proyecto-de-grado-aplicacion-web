"""
Forms for transacciones app.
"""
from __future__ import annotations

from django import forms

from fidelizacion import services as loyalty
from .models import Transaccion


class TransaccionForm(forms.ModelForm):
    """Formulario para registrar una transacción y gestionar puntos de fidelización."""

    puntos_a_canjear = forms.IntegerField(
        required=False,
        min_value=0,
        label="Puntos a canjear",
        help_text="Opcional. Descontará del saldo del cliente al confirmar la transacción.",
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "0"}),
    )

    class Meta:
        model = Transaccion
        fields = ["cita", "subtotal", "monto", "metodo_pago"]
        widgets = {
            "cita": forms.Select(attrs={"class": "form-select"}),
            "subtotal": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "0.01"}),
            "monto": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "0.01"}),
            "metodo_pago": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)
        self.cliente = None
        self.available_points = 0
        self.config = loyalty.get_config()
        cita = self.initial.get("cita") or self.data.get("cita")
        if cita:
            from citas.models import Cita  # import local to avoid circular
            try:
                self.cliente = Cita.objects.select_related("cliente").get(pk=cita).cliente
            except Cita.DoesNotExist:
                self.cliente = None
        if self.instance.pk and not self.cliente and hasattr(self.instance, "cita"):
            self.cliente = self.instance.cita.cliente

        if self.cliente:
            self.available_points = loyalty.obtener_saldo(self.cliente)
            self.fields["puntos_a_canjear"].help_text += f" | Saldo disponible: {self.available_points} pts"

    def clean(self):
        cleaned = super().clean()
        subtotal = cleaned.get("subtotal") or 0
        monto = cleaned.get("monto") or 0
        puntos_a_canjear = cleaned.get("puntos_a_canjear") or 0
        cita = cleaned.get("cita")

        if subtotal <= 0:
            self.add_error("subtotal", "El subtotal debe ser mayor a cero.")
        if monto < 0:
            self.add_error("monto", "El monto pagado no puede ser negativo.")
        if puntos_a_canjear < 0:
            self.add_error("puntos_a_canjear", "Los puntos a canjear deben ser un número positivo.")

        if cita:
            self.cliente = cita.cliente
            saldo = loyalty.obtener_saldo(self.cliente)
            if puntos_a_canjear > saldo:
                self.add_error("puntos_a_canjear", "El cliente no tiene puntos suficientes para canjear.")

        return cleaned

    def get_cliente(self):
        if self.cliente:
            return self.cliente
        cleaned = getattr(self, "cleaned_data", {})
        cita = cleaned.get("cita")
        if cita:
            self.cliente = cita.cliente
        return self.cliente
