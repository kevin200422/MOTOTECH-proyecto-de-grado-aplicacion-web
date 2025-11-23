# -*- coding: utf-8 -*-
from datetime import date, datetime, timedelta
from io import BytesIO
import csv
from collections import defaultdict
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, F, Q
from django.db.models.functions import TruncMonth, ExtractWeekDay, ExtractHour
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render

# MODELOS
from clientes.models import Cliente
from servicios.models import Servicio
from citas.models import Cita

# ---------- Helpers ----------
def _parse_date(s, default=None):
    if not s:
        return default
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return default

def _filtered_citas(request):
    hoy = date.today()
    desde = _parse_date(request.GET.get("desde"), default=hoy.replace(day=1) - timedelta(days=180))
    hasta = _parse_date(request.GET.get("hasta"), default=hoy)
    estados = request.GET.getlist("estado")
    qs = Cita.objects.select_related("servicio", "cliente").filter(
        fecha_inicio__date__range=(desde, hasta)
    )
    if estados:
        qs = qs.filter(estado__in=estados)
    return qs, desde, hasta, estados

# ---------- Vista HTML ----------
@login_required
def overview(request):
    hoy = date.today()
    desde_sug = (hoy.replace(day=1) - timedelta(days=180)).strftime("%Y-%m-%d")
    hasta_sug = hoy.strftime("%Y-%m-%d")
    estados = ["pendiente", "en_proceso", "completada", "cancelada"]
    return render(request, "dashboard/overview.html", {
        "desde_sugerido": desde_sug,
        "hasta_sugerido": hasta_sug,
        "estados_posibles": estados,
    })

# ---------- APIs base ----------
@login_required
def api_kpis(request):
    qs, _, _, _ = _filtered_citas(request)
    agg = qs.aggregate(
        total_citas=Count("id"),
        ingresos=Sum(F("servicio__precio")),  # AJUSTA SI tienes Cita.total
    )
    data = {
        "clientes": Cliente.objects.count(),
        "servicios": Servicio.objects.count(),
        "citas": agg["total_citas"] or 0,
        "ingresos": float(agg["ingresos"] or 0.0),
    }
    return JsonResponse(data)

@login_required
def api_timeseries(request):
    qs, _, _, _ = _filtered_citas(request)
    base = (
        qs.annotate(mes=TruncMonth("fecha_inicio"))
          .values("mes")
          .annotate(
              citas=Count("id"),
              ingresos=Sum(F("servicio__precio")),  # AJUSTA SI tienes Cita.total
          )
          .order_by("mes")
    )
    labels, series_citas, series_ingresos = [], [], []
    for row in base:
        labels.append(row["mes"].strftime("%Y-%m"))
        series_citas.append(row["citas"])
        series_ingresos.append(float(row["ingresos"] or 0.0))

    # Pronóstico 3 meses (sklearn si está, sino naive)
    forecast_labels, forecast_ingresos = [], []
    try:
        from sklearn.linear_model import LinearRegression
        import numpy as np
        if labels:
            months_index = np.arange(len(labels)).reshape(-1, 1)
            # característica simple estacional: mes (1-12)
            seasonal = np.array([int(l[-2:]) for l in labels]).reshape(-1,1)
            X = np.hstack([months_index, seasonal])
            y = np.array(series_ingresos, dtype=float)

            model = LinearRegression()
            model.fit(X, y)

            base_dt = datetime.strptime(labels[-1] + "-01", "%Y-%m-%d")
            for i in range(1, 4):
                pred_month = (base_dt.replace(day=1) + timedelta(days=32*i)).replace(day=1)
                label = pred_month.strftime("%Y-%m")
                x_next = [[len(labels)+i-1, pred_month.month]]
                yhat = float(model.predict(x_next)[0])
                forecast_labels.append(label)
                forecast_ingresos.append(round(max(yhat, 0.0), 2))
    except Exception:
        if series_ingresos:
            last = series_ingresos[-1]
            base_dt = datetime.strptime(labels[-1] + "-01", "%Y-%m-%d") if labels else datetime.today()
            for i in range(1, 4):
                pred_month = (base_dt.replace(day=1) + timedelta(days=32*i)).replace(day=1)
                forecast_labels.append(pred_month.strftime("%Y-%m"))
                forecast_ingresos.append(float(last))

    return JsonResponse({
        "labels": labels,
        "citas": series_citas,
        "ingresos": series_ingresos,
        "forecast_labels": forecast_labels,
        "forecast_ingresos": forecast_ingresos,
    })

@login_required
def api_top_servicios(request):
    qs, _, _, _ = _filtered_citas(request)
    top = (
        qs.values("servicio__nombre")
          .annotate(ingresos=Sum(F("servicio__precio")), cantidad=Count("id"))
          .order_by("-ingresos")[:10]
    )
    labels = [r["servicio__nombre"] or "—" for r in top]
    ingresos = [float(r["ingresos"] or 0.0) for r in top]
    cantidad = [int(r["cantidad"]) for r in top]
    return JsonResponse({"labels": labels, "ingresos": ingresos, "cantidad": cantidad})

@login_required
def api_estado_pastel(request):
    qs, _, _, _ = _filtered_citas(request)
    estado = (qs.values("estado").annotate(n=Count("id")).order_by("-n"))
    labels = [r["estado"] or "—" for r in estado]
    valores = [r["n"] for r in estado]
    return JsonResponse({"labels": labels, "values": valores})

# ---------- APIs BI avanzadas ----------
@login_required
def api_heatmap_dia_hora(request):
    """
    Heatmap de volumen por día de la semana (1=Domingo con ExtractWeekDay en SQLite? En Django: 1=Dom, 7=Sáb)
    y por hora (0-23) usando fecha_inicio.
    """
    qs, _, _, _ = _filtered_citas(request)
    rows = (
        qs.annotate(dow=ExtractWeekDay("fecha_inicio"), hh=ExtractHour("fecha_inicio"))
          .values("dow", "hh")
          .annotate(n=Count("id"))
          .order_by("dow", "hh")
    )
    # Mapa 7x24
    heat = [[0]*24 for _ in range(7)]
    for r in rows:
        dow = (r["dow"] or 1) - 1  # 0..6
        hh = r["hh"] or 0
        if 0 <= dow <= 6 and 0 <= hh <= 23:
            heat[dow][hh] = r["n"]
    return JsonResponse({"matrix": heat, "labels_dow": ["Dom","Lun","Mar","Mié","Jue","Vie","Sáb"], "labels_hh": list(range(24))})

@login_required
def api_cohortes(request):
    """
    Cohortes mensuales por mes-de-alta del cliente: cuántos vuelven X meses después a tener citas.
    Heurística: mes de la primera cita del cliente como "mes de alta".
    """
    qs, _, _, _ = _filtered_citas(request)

    # primera cita por cliente (en rango)
    first_by_client = (qs.values("cliente_id")
                         .annotate(m0=TruncMonth(F("fecha_inicio")))
                         .values("cliente_id", "m0"))

    # Para facilitar, traemos todas las citas del rango por cliente/mes:
    citas_mes = (qs.annotate(m=TruncMonth("fecha_inicio"))
                   .values("cliente_id", "m")
                   .annotate(n=Count("id")))

    # Normalizamos en dict {cliente: mes0}
    alta = {}
    for r in first_by_client:
        alta[r["cliente_id"]] = r["m0"]

    # Cohortes: {mes0: {offset: count}}
    cohorts = defaultdict(lambda: defaultdict(int))
    base_counts = defaultdict(int)  # tamaño cohorte

    for r in citas_mes:
        cid = r["cliente_id"]
        m = r["m"]
        m0 = alta.get(cid)
        if not m0: 
            continue
        base_counts[m0] += 0  # asegura clave
        offset = (m.year - m0.year) * 12 + (m.month - m0.month)
        if offset >= 0:
            cohorts[m0][offset] += r["n"]
            if offset == 0:
                base_counts[m0] += r["n"]

    # construimos tabla: filas=cohortes (mes0), columnas=offset 0..5
    labels_rows = sorted(cohorts.keys())
    max_off = 5
    matrix = []
    for m0 in labels_rows:
        row = []
        for off in range(0, max_off+1):
            row.append(cohorts[m0].get(off, 0))
        matrix.append(row)

    # tasas de retención (normaliza por base de la cohorte)
    retention = []
    for i, m0 in enumerate(labels_rows):
        base = max(base_counts.get(m0) or 1, 1)
        retention.append([round(c / base, 3) for c in matrix[i]])

    labels_rows = [m0.strftime("%Y-%m") for m0 in labels_rows]
    labels_cols = [f"M+{i}" for i in range(0, max_off+1)]
    return JsonResponse({"labels_rows": labels_rows, "labels_cols": labels_cols, "retention": retention})

@login_required
def api_ltv(request):
    """
    LTV aproximado: suma de ingresos por cliente en la ventana filtrada / número de clientes activos.
    También devolvemos top clientes por valor.
    """
    qs, _, _, _ = _filtered_citas(request)
    por_cliente = (qs.values("cliente_id", "cliente__nombre")
                     .annotate(ingresos=Sum(F("servicio__precio")), n=Count("id"))
                     .order_by("-ingresos"))
    total_clientes = por_cliente.count() or 1
    total_ingresos = float(sum(float(r["ingresos"] or 0.0) for r in por_cliente))
    ltv_prom = total_ingresos / total_clientes if total_clientes else 0.0
    top = list(por_cliente[:10])
    # serializa
    labels = [r["cliente__nombre"] or f"ID {r['cliente_id']}" for r in top]
    valores = [float(r["ingresos"] or 0.0) for r in top]
    return JsonResponse({
        "ltv_promedio": round(ltv_prom, 2),
        "labels": labels,
        "valores": valores
    })

@login_required
def api_repeat_rate(request):
    """
    Repetición: % de clientes con 2+ citas en la ventana.
    """
    qs, _, _, _ = _filtered_citas(request)
    por_cliente = (qs.values("cliente_id").annotate(n=Count("id")))
    total = por_cliente.count() or 1
    repetidores = sum(1 for r in por_cliente if r["n"] >= 2)
    repeat_rate = repetidores / total if total else 0.0
    return JsonResponse({"repeat_rate": round(repeat_rate, 3), "total": total, "repetidores": repetidores})

@login_required
def api_inventario_metricas(request):
    """
    Métricas de inventario enriquecidas con rotación, cobertura, alertas y pronósticos
    basados en los movimientos reales del módulo de inventario.
    """
    try:
        from inventario.models import Repuesto, MovimientoInventario, CategoriaRepuesto
    except Exception:
        return JsonResponse({
            "rotacion": 0.0,
            "cobertura_dias": 0.0,
            "sku_bajos": 0,
            "valor_stock": 0.0,
            "margen_potencial": 0.0,
            "consumo_mensual_estimado": 0.0,
            "riesgo_sin_stock": 0,
            "sin_movimientos": 0,
            "criticos": [],
            "categorias": [],
        })

    _, desde, hasta, _ = _filtered_citas(request)
    hasta = hasta or date.today()
    desde = desde or (hasta - timedelta(days=180))
    ventana_dias = max((hasta - desde).days, 1)
    ventana_mov_inicio = max(hasta - timedelta(days=90), desde)
    ventana_mov_dias = max((hasta - ventana_mov_inicio).days, 1)

    salidas_qs = (
        MovimientoInventario.objects.filter(
            tipo=MovimientoInventario.Tipo.SALIDA,
            fecha__date__range=(ventana_mov_inicio, hasta),
        )
        .values("repuesto_id")
        .annotate(total=Sum("cantidad"))
    )
    salidas_map = {row["repuesto_id"]: float(row["total"] or 0.0) for row in salidas_qs}

    repuestos = list(Repuesto.objects.all())
    stock_total = sum(int(getattr(rep, "stock", 0) or 0) for rep in repuestos)
    sku_bajos = sum(1 for rep in repuestos if getattr(rep, "bajo_stock", False))
    valor_stock = sum((rep.valor_inventario or Decimal("0")) for rep in repuestos)
    valor_potencial = sum((rep.valor_potencial or Decimal("0")) for rep in repuestos)
    margen_potencial = valor_potencial - valor_stock

    consumo_total = sum(salidas_map.get(rep.id, 0.0) for rep in repuestos)
    consumo_diario_prom = consumo_total / ventana_mov_dias if ventana_mov_dias else 0.0
    consumo_mensual_estimado = consumo_diario_prom * 30.0

    rotacion = 0.0
    if stock_total > 0 and consumo_total > 0:
        rotacion = (consumo_total / ventana_mov_dias) * 30.0 / max(float(stock_total), 1.0)

    cobertura_global = 0.0
    if consumo_diario_prom > 0:
        cobertura_global = float(stock_total) / consumo_diario_prom

    categoria_choices = {}
    try:
        categoria_choices = dict(Repuesto._meta.get_field("categoria").choices)
    except Exception:
        try:
            categoria_choices = dict(CategoriaRepuesto.choices)
        except Exception:
            categoria_choices = {}

    categorias_stats = {}
    criticos_candidates = []
    sin_movimientos = 0
    riesgo_sin_stock = 0

    for rep in repuestos:
        total_salidas_rep = salidas_map.get(rep.id, 0.0)
        consumo_diario = total_salidas_rep / ventana_mov_dias if ventana_mov_dias else 0.0
        cobertura = rep.stock / consumo_diario if consumo_diario > 0 else None
        cobertura_val = round(cobertura, 1) if cobertura is not None else None
        tiempo_reposicion = int(getattr(rep, "tiempo_reposicion_dias", 0) or 0)
        riesgo = False
        if cobertura is not None:
            riesgo = cobertura <= max(tiempo_reposicion, 15)
            if riesgo:
                riesgo_sin_stock += 1
            criticos_candidates.append({
                "id": rep.id,
                "nombre": rep.nombre,
                "categoria": rep.get_categoria_display() if hasattr(rep, "get_categoria_display") else rep.categoria,
                "stock": int(rep.stock or 0),
                "cobertura_dias": cobertura_val,
                "tiempo_reposicion": tiempo_reposicion,
                "consumo_diario": round(consumo_diario, 2),
                "riesgo": riesgo,
            })
        else:
            sin_movimientos += 1

        cat_key = rep.categoria or "otros"
        cat_entry = categorias_stats.setdefault(
            cat_key,
            {
                "nombre": categoria_choices.get(cat_key, cat_key.title()),
                "valor": 0.0,
                "consumo": 0.0,
                "unidades": 0,
                "criticos": 0,
            },
        )
        cat_entry["valor"] += float(rep.valor_inventario or 0.0)
        cat_entry["consumo"] += total_salidas_rep
        cat_entry["unidades"] += int(rep.stock or 0)
        if getattr(rep, "bajo_stock", False):
            cat_entry["criticos"] += 1

    criticos = sorted(
        criticos_candidates,
        key=lambda item: item["cobertura_dias"] if item["cobertura_dias"] is not None else float("inf"),
    )[:5]

    categorias = []
    for data in categorias_stats.values():
        rot_cat = 0.0
        if data["unidades"] > 0 and data["consumo"] > 0:
            rot_cat = (data["consumo"] / ventana_mov_dias) * 30.0 / max(float(data["unidades"]), 1.0)
        categorias.append({
            "nombre": data["nombre"],
            "valor": round(data["valor"], 2),
            "rotacion": round(rot_cat, 2),
            "criticos": data["criticos"],
        })

    return JsonResponse({
        "rotacion": round(rotacion, 2),
        "cobertura_dias": round(cobertura_global, 1) if cobertura_global else 0.0,
        "sku_bajos": int(sku_bajos),
        "valor_stock": round(float(valor_stock), 2),
        "margen_potencial": round(float(margen_potencial), 2),
        "consumo_mensual_estimado": round(consumo_mensual_estimado, 1),
        "riesgo_sin_stock": int(riesgo_sin_stock),
        "sin_movimientos": int(sin_movimientos),
        "criticos": criticos,
        "categorias": categorias,
    })

@login_required
def api_margen_servicios(request):
    """
    Margen por servicio: ingreso - costo. Si no hay costo, margen = ingreso.
    Intenta usar Servicio.costo (o costo_estandar). AJUSTA segun tu modelo real.
    """
    try:
        costo_field = "costo"
        Servicio._meta.get_field(costo_field)
    except Exception:
        costo_field = None

    qs, _, _, _ = _filtered_citas(request)
    base = (qs.values("servicio__nombre")
              .annotate(ingresos=Sum(F("servicio__precio")), n=Count("id"))
              .order_by("-ingresos"))
    labels, ingresos, costos, margen = [], [], [], []
    for r in base[:10]:
        nombre = r["servicio__nombre"] or "—"
        ing = float(r["ingresos"] or 0.0)
        if costo_field:
            # costo por servicio * cantidad
            try:
                s = Servicio.objects.get(nombre=nombre)
                c_unit = float(getattr(s, costo_field) or 0.0)
                c = c_unit * float(r["n"])
            except Exception:
                c = 0.0
        else:
            c = 0.0
        labels.append(nombre)
        ingresos.append(ing)
        costos.append(round(c, 2))
        margen.append(round(ing - c, 2))
    return JsonResponse({"labels": labels, "ingresos": ingresos, "costos": costos, "margen": margen})

@login_required
def api_funnel_citas(request):
    """
    Embudo simple por estado (Pendiente -> En proceso -> Completada), Cancelada aparte.
    """
    qs, _, _, _ = _filtered_citas(request)
    def c(state):
        return qs.filter(estado=state).count()
    data = {
        "pendiente": c("pendiente"),
        "en_proceso": c("en_proceso"),
        "completada": c("completada"),
        "cancelada": c("cancelada"),
    }
    return JsonResponse(data)

# ---------- Export ----------
@login_required
def export_citas_csv(request):
    qs, _, _, _ = _filtered_citas(request)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = "attachment; filename=citas.csv"
    writer = csv.writer(response)
    writer.writerow(["Fecha", "Cliente", "Servicio", "Estado", "IngresoEstimado"])
    for c in qs.order_by("-fecha_inicio"):
        writer.writerow([
            c.fecha_inicio.strftime("%Y-%m-%d %H:%M"),
            getattr(c.cliente, "nombre", ""),
            getattr(c.servicio, "nombre", ""),
            c.estado,
            getattr(c.servicio, "precio", 0.0),  # AJUSTA si usas Cita.total
        ])
    return response

@login_required
def export_citas_xlsx(request):
    try:
        import pandas as pd
        qs, _, _, _ = _filtered_citas(request)
        rows = []
        for c in qs.order_by("-fecha_inicio"):
            rows.append({
                "Fecha": c.fecha_inicio.strftime("%Y-%m-%d %H:%M"),
                "Cliente": getattr(c.cliente, "nombre", ""),
                "Servicio": getattr(c.servicio, "nombre", ""),
                "Estado": c.estado,
                "IngresoEstimado": float(getattr(c.servicio, "precio", 0.0)),
            })
        df = pd.DataFrame(rows)
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Citas")
        output.seek(0)
        resp = HttpResponse(
            output.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        resp["Content-Disposition"] = 'attachment; filename="citas.xlsx"'
        return resp
    except Exception:
        return export_citas_csv(request)
