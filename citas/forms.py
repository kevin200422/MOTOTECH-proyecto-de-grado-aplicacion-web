# citas/forms.py
from datetime import timedelta

from django import forms

from .models import Cita
from clientes.models import Cliente
from servicios.models import Servicio
from vehiculos.models import Vehiculo

_DT_FORMAT = "%Y-%m-%dT%H:%M"  # para input type="datetime-local"

# Campos base obligatorios (ajusta si tus nombres difieren)
_BASE_FIELDS = ["cliente", "vehiculo", "servicio", "fecha_inicio", "fecha_fin", "estado"]
# Añadimos 'notas' solo si existe en el modelo
if hasattr(Cita, "notas"):
    _BASE_FIELDS.append("notas")

class CitaForm(forms.ModelForm):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.all().order_by("nombre"),
        required=True,
        label="Cliente",
        help_text="Selecciona el cliente",
    )
    servicio = forms.ModelChoiceField(
        queryset=Servicio.objects.filter(activo=True).order_by("nombre"),
        required=True,
        label="Servicio",
    )

    class Meta:
        model = Cita
        fields = _BASE_FIELDS
        widgets = {
            "fecha_inicio": forms.DateTimeInput(attrs={"type": "datetime-local"}, format=_DT_FORMAT),
            "fecha_fin": forms.DateTimeInput(attrs={"type": "datetime-local"}, format=_DT_FORMAT),
        }
        # Si existe 'notas', le asignamos widget Textarea; si no existe, no pasa nada
        if hasattr(Cita, "notas"):
            widgets["notas"] = forms.Textarea(attrs={"rows": 3})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Etiqueta enriquecida para cliente
        self.fields["cliente"].label_from_instance = (
            lambda c: f"{c.nombre}" + (f" · {getattr(c, 'telefono', '')}" if getattr(c, 'telefono', '') else "")
        )
        # Vehículos dinámicos según cliente
        self.fields["vehiculo"].queryset = Vehiculo.objects.none()
        if "cliente" in self.data:
            try:
                cliente_id = int(self.data.get("cliente"))
                self.fields["vehiculo"].queryset = Vehiculo.objects.filter(
                    cliente_id=cliente_id
                ).order_by("placa")
            except (TypeError, ValueError):
                pass
        elif self.instance.pk and getattr(self.instance, "cliente_id", None):
            self.fields["vehiculo"].queryset = Vehiculo.objects.filter(
                cliente_id=self.instance.cliente_id
            ).order_by("placa")

    def clean(self):
        cleaned = super().clean()
        fi = cleaned.get("fecha_inicio")
        ff = cleaned.get("fecha_fin")
        servicio = cleaned.get("servicio")

        # Si no se diligencia fin, lo calculamos con la duracion del servicio (si existe)
        if fi and not ff and servicio and getattr(servicio, "duracion_minutos", None):
            ff = cleaned["fecha_fin"] = fi + timedelta(minutes=servicio.duracion_minutos)

        if fi and ff and ff <= fi:
            self.add_error("fecha_fin", "La fecha fin debe ser posterior a la fecha inicio.")
        return cleaned
