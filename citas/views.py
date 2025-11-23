# citas/views.py
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
import csv
from .models import Cita
from .forms import CitaForm
from vehiculos.models import Vehiculo
from servicios.models import Servicio
from clientes.models import Cliente

# ---------- Contexto compartido ----------
class CitaDuracionesMixin:
    """Inyecta duraciones de servicios para autocompletar fecha fin en el formulario."""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["duraciones_servicio"] = {
            s.id: s.duracion_minutos for s in Servicio.objects.filter(activo=True)
        }
        return ctx

# ---------- LISTA CON BUSCADOR / FILTROS / ORDEN ----------
class CitaListView(ListView):
    model = Cita
    template_name = "citas/list.html"
    context_object_name = "object_list"
    paginate_by = 10

    def get_queryset(self):
        qs = Cita.objects.select_related("cliente", "vehiculo", "servicio")

        q = self.request.GET.get("q", "").strip()
        estado = self.request.GET.get("estado", "").strip()
        desde = self.request.GET.get("desde", "").strip()
        hasta = self.request.GET.get("hasta", "").strip()
        o = self.request.GET.get("o", "").strip()

        if q:
            qs = qs.filter(
                Q(cliente__nombre__icontains=q)
                | Q(vehiculo__placa__icontains=q)
                | Q(servicio__nombre__icontains=q)
                | Q(notas__icontains=q)
            )

        if estado:
            qs = qs.filter(estado=estado)

        # Rango fechas (se compara contra fecha_inicio)
        if desde:
            try:
                dt = timezone.datetime.fromisoformat(desde)
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt, timezone.get_current_timezone())
                qs = qs.filter(fecha_inicio__gte=dt)
            except Exception:
                pass
        if hasta:
            try:
                dt = timezone.datetime.fromisoformat(hasta)
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt, timezone.get_current_timezone())
                qs = qs.filter(fecha_inicio__lte=dt)
            except Exception:
                pass

        allowed = {
            "fecha_inicio", "-fecha_inicio",
            "cliente__nombre", "-cliente__nombre",
            "vehiculo__placa", "-vehiculo__placa",
            "servicio__nombre", "-servicio__nombre",
            "estado", "-estado",
        }
        qs = qs.order_by(o if o in allowed else "-fecha_inicio")
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["o"] = self.request.GET.get("o", "")
        ctx["estado"] = self.request.GET.get("estado", "")
        ctx["desde"] = self.request.GET.get("desde", "")
        ctx["hasta"] = self.request.GET.get("hasta", "")
        # Opciones de estado (ajusta a tus choices reales)
        ctx["ESTADOS"] = [
            ("pendiente", "Pendiente"),
            ("confirmada", "Confirmada"),
            ("en_proceso", "En proceso"),
            ("completada", "Completada"),
            ("cancelada", "Cancelada"),
        ]
        queryset = self.get_queryset()
        ctx["summary"] = {
            "total": queryset.count(),
            "activas": queryset.filter(estado__in=["pendiente", "confirmada", "en_proceso"]).count(),
            "completadas": queryset.filter(estado="completada").count(),
            "canceladas": queryset.filter(estado="cancelada").count(),
        }
        ctx["next_cita"] = queryset.order_by("fecha_inicio").first()
        return ctx


# ---------- DETALLE ----------
class CitaDetailView(DetailView):
    model = Cita
    template_name = "citas/detail.html"
    context_object_name = "cita"


# ---------- CREAR ----------
class CitaCreateView(CitaDuracionesMixin, CreateView):
    model = Cita
    form_class = CitaForm
    template_name = "citas/form.html"
    success_url = reverse_lazy("citas:list")

    def form_valid(self, form):
        messages.success(self.request, "Cita creada correctamente.")
        return super().form_valid(form)


# ---------- EDITAR ----------
class CitaUpdateView(CitaDuracionesMixin, UpdateView):
    model = Cita
    form_class = CitaForm
    template_name = "citas/form.html"
    success_url = reverse_lazy("citas:list")

    def form_valid(self, form):
        messages.success(self.request, "Cita actualizada correctamente.")
        return super().form_valid(form)


# ---------- ELIMINAR ----------
class CitaDeleteView(DeleteView):
    model = Cita
    template_name = "citas/confirm_delete.html"
    success_url = reverse_lazy("citas:list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Cita eliminada.")
        return super().delete(request, *args, **kwargs)


# ---------- API: Vehiculos por cliente (para selects dependientes) ----------
def api_vehiculos_por_cliente(request):
    cliente_id = request.GET.get("cliente")
    items = []
    if cliente_id and cliente_id.isdigit():
        for v in Vehiculo.objects.filter(cliente_id=int(cliente_id)).order_by("placa"):
            items.append({"id": v.id, "text": f"{v.placa} - {getattr(v, 'marca', '')} {getattr(v, 'modelo', '')}".strip()})
    return JsonResponse({"results": items})


# ---------- Export CSV ----------
# ---------- Export CSV ----------
def citas_export_csv(request):
    qs = CitaListView()
    qs.request = request
    queryset = qs.get_queryset()

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="citas.csv"'
    writer = csv.writer(response)
    writer.writerow(["ID", "Cliente", "Vehiculo", "Servicio", "Inicio", "Fin", "Estado", "Notas"])
    for c in queryset:
        writer.writerow([
            c.id,
            getattr(c.cliente, "nombre", ""),
            getattr(c.vehiculo, "placa", ""),
            getattr(c.servicio, "nombre", ""),
            timezone.localtime(c.fecha_inicio).strftime("%Y-%m-%d %H:%M"),
            timezone.localtime(c.fecha_fin).strftime("%Y-%m-%d %H:%M") if c.fecha_fin else "",
            c.estado,
            getattr(c, "notas", "").replace("\n", " "),
        ])
    return response



# ---------- Calendar JSON (para FullCalendar o dashboard) ----------
def calendar_json(request):
    # Devuelve eventos minimos: title, start, end, url
    eventos = []
    for c in Cita.objects.select_related("cliente", "vehiculo", "servicio"):
        eventos.append({
            "id": c.id,
            "title": f"{getattr(c.servicio, 'nombre', 'Servicio')} - {getattr(c.cliente, 'nombre', '')}",
            "start": timezone.localtime(c.fecha_inicio).isoformat(),
            "end": timezone.localtime(c.fecha_fin).isoformat() if c.fecha_fin else None,
            "url": reverse_lazy("citas:detail", args=[c.id]),
            "extendedProps": {
                "estado": c.estado,
                "vehiculo": getattr(c.vehiculo, "placa", ""),
            }
        })
    return JsonResponse(eventos, safe=False)


# ---------- ICS individual ----------
def cita_ics(request, pk):
    c = Cita.objects.select_related("cliente", "vehiculo", "servicio").get(pk=pk)
    inicio = timezone.localtime(c.fecha_inicio).strftime("%Y%m%dT%H%M%S")
    fin = timezone.localtime(c.fecha_fin).strftime("%Y%m%dT%H%M%S") if c.fecha_fin else ""
    summary = f"{getattr(c.servicio, 'nombre', 'Cita')} - {getattr(c.cliente, 'nombre', '')}"
    description = getattr(c, "notas", "").replace("\n", " ")
    ics = (
        "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//TuTaller//Citas//ES\n"
        "BEGIN:VEVENT\n"
        f"UID:cita-{c.id}@tutaller\n"
        f"DTSTART:{inicio}\n" +
        (f"DTEND:{fin}\n" if fin else "") +
        f"SUMMARY:{summary}\n"
        f"DESCRIPTION:{description}\n"
        "END:VEVENT\nEND:VCALENDAR\n"
    )
    resp = HttpResponse(ics, content_type="text/calendar")
    resp["Content-Disposition"] = f'attachment; filename="cita-{c.id}.ics"'
    return resp
