# citas/templatetags/querytools.py
from urllib.parse import urlencode
from django import template

register = template.Library()

def _get_request(context):
    request = context.get("request")
    if request is None:
        raise RuntimeError(
            "querytools requires 'request' in context. "
            "Asegúrate de tener 'django.template.context_processors.request' en TEMPLATES."
        )
    return request

@register.simple_tag(takes_context=True)
def keep_query(context, **override):
    """
    Mantiene todos los parámetros actuales y aplica overrides, e.g.:
    href="?{% keep_query(page=1, o='-fecha') %}"
    """
    request = _get_request(context)
    q = request.GET.copy()
    for k, v in override.items():
        if v is None:
            q.pop(k, None)
        else:
            q[k] = v
    return q.urlencode()

@register.simple_tag(takes_context=True)
def keep_query_except(context, *remove, **override):
    """
    Mantiene la query actual, eliminando claves en *remove* y aplicando overrides.
    Ejemplo: {% keep_query_except 'page' 'o' q=busqueda %}
    """
    request = _get_request(context)
    q = {k: v for k, v in request.GET.items() if k not in remove}
    q.update({k: v for k, v in override.items() if v is not None})
    return urlencode(q)

@register.simple_tag(takes_context=True)
def toggle_order(context, field_name):
    """
    Alterna el orden del parámetro 'o' entre 'campo' y '-campo'.
    Uso: href=\"?{% toggle_order 'nombre' %}\"
    """
    request = _get_request(context)
    current = request.GET.get("o", "")
    if current == field_name:
        new_o = f"-{field_name}"
    elif current == f"-{field_name}":
        new_o = field_name
    else:
        new_o = field_name
    q = request.GET.copy()
    q["o"] = new_o
    return q.urlencode()
