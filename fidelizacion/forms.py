from __future__ import annotations



import json



from django import forms



from fidelizacion.models import ConfigPuntos





class AjustePuntosForm(forms.Form):

    puntos = forms.IntegerField(

        label="Puntos",

        help_text="Use valores positivos para bonificar y negativos para descontar.",

        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "+100"}),

    )

    motivo = forms.CharField(

        required=False,

        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),

        help_text="Motivo o nota interna del ajuste.",

    )





class ConfigPuntosForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        niveles_field = self.fields["niveles_config"]

        niveles_field.help_text = (

            "JSON con niveles y beneficios. Ejemplo: "

            "{'Bronce': {'umbral': 0, 'multiplicador': 1}, "

            "'Oro': {'umbral': 8000, 'multiplicador': 1.25, 'bono_fijo': 40}}"

        )

        niveles_field.widget.attrs.setdefault("spellcheck", "false")

        niveles_field.widget.attrs.setdefault(

            "placeholder",

            "{'Bronce': {'umbral': 0, 'multiplicador': 1}, 'Plata': {'umbral': 5000, 'multiplicador': 1.1}}",

        )

    class Meta:

        model = ConfigPuntos

        fields = [

            "puntos_por_monto",

            "monto_base_cop",

            "puntos_equivalencia",

            "valor_redencion_cop",

            "puntos_max_por_factura",

            "exclusiones_servicios",

            "exclusiones_categorias",

            "niveles_config",

        ]

        widgets = {

            "exclusiones_servicios": forms.SelectMultiple(attrs={"class": "form-select"}),

            "niveles_config": forms.Textarea(attrs={"class": "form-control", "rows": 3}),

            "exclusiones_categorias": forms.Textarea(attrs={"class": "form-control", "rows": 2}),

        }



    def clean_niveles_config(self):

        data = self.cleaned_data.get("niveles_config") or {}

        if isinstance(data, str):

            texto = data.strip()

            if not texto:

                return {}

            try:

                data = json.loads(texto)

            except json.JSONDecodeError as exc:

                raise forms.ValidationError("Debe ingresar un JSON valido.") from exc

        if not isinstance(data, dict):

            raise forms.ValidationError("El formato de niveles debe ser un diccionario.")



        normalizado = {}

        for nombre, valor in data.items():

            nombre_str = str(nombre).strip()

            if not nombre_str:

                raise forms.ValidationError("Los nombres de nivel no pueden estar vacios.")



            if isinstance(valor, str):

                valor_texto = valor.strip()

                if not valor_texto:

                    valor = 0

                elif valor_texto.startswith("{"):

                    try:

                        valor = json.loads(valor_texto)

                    except json.JSONDecodeError as exc:
                        raise forms.ValidationError(f"El nivel '{nombre_str}' contiene un JSON invalido.") from exc
                else:

                    valor = valor_texto



            if isinstance(valor, dict):

                raw_umbral = valor.get("umbral", valor.get("threshold", valor.get("minimo")))

                raw_multiplicador = valor.get("multiplicador", valor.get("factor", 1))

                raw_bono = valor.get("bono_fijo", valor.get("bono", 0))

            else:

                raw_umbral = valor

                raw_multiplicador = 1

                raw_bono = 0



            try:

                umbral = int(raw_umbral or 0)

            except (TypeError, ValueError) as exc:
                raise forms.ValidationError(f"El umbral para el nivel '{nombre_str}' debe ser un entero.") from exc
            if umbral < 0:
                raise forms.ValidationError(f"El umbral para el nivel '{nombre_str}' no puede ser negativo.")


            try:

                multiplicador = float(raw_multiplicador or 1)

            except (TypeError, ValueError) as exc:
                raise forms.ValidationError(f"El multiplicador del nivel '{nombre_str}' debe ser numerico.") from exc
            if multiplicador < 0:
                raise forms.ValidationError(f"El multiplicador del nivel '{nombre_str}' no puede ser negativo.")


            try:

                bono_fijo = int(raw_bono or 0)

            except (TypeError, ValueError) as exc:
                raise forms.ValidationError(f"El bono fijo del nivel '{nombre_str}' debe ser un entero.") from exc
            if bono_fijo < 0:
                raise forms.ValidationError(f"El bono fijo del nivel '{nombre_str}' no puede ser negativo.")


            normalizado[nombre_str] = {

                "umbral": umbral,

                "multiplicador": round(multiplicador, 4),

                "bono_fijo": bono_fijo,

            }



        return normalizado

