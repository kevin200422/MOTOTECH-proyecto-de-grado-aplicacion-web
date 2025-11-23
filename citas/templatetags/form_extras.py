# taller_mecanico/citas/templatetags/form_extras.py
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name="add_class")
def add_class(field, css):
    """
    Uso: {{ form.campo|add_class:"form-control" }}
    Conserva clases existentes y añade las nuevas.
    """
    if hasattr(field, "as_widget"):
        attrs = field.field.widget.attrs.copy()
        # combinar clases existentes con las nuevas
        current = attrs.get("class", "")
        classes = f"{current} {css}".strip() if current else css
        attrs["class"] = classes
        return field.as_widget(attrs=attrs)
    return field

@register.filter(name="attr")
def attr(field, arg):
    """
    Establece cualquier atributo: {{ form.campo|attr:"placeholder:Buscar..." }}
    o múltiples: {{ form.campo|attr:"data-x:1|autocomplete:off" }}
    """
    if not hasattr(field, "as_widget"):
        return field
    attrs = field.field.widget.attrs.copy()
    for pair in str(arg).split("|"):
        if ":" in pair:
            k, v = pair.split(":", 1)
            attrs[k.strip()] = v.strip()
    return field.as_widget(attrs=attrs)
