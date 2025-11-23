# -*- coding: utf-8 -*-
from django.urls import path
from . import views

urlpatterns = [
    path("", views.overview, name="overview"),

    # APIs base
    path("api/kpis/", views.api_kpis, name="api_kpis"),
    path("api/timeseries/", views.api_timeseries, name="api_timeseries"),
    path("api/top-servicios/", views.api_top_servicios, name="api_top_servicios"),
    path("api/estado-pastel/", views.api_estado_pastel, name="api_estado_pastel"),

    # APIs BI avanzadas
    path("api/heatmap-dia-hora/", views.api_heatmap_dia_hora, name="api_heatmap_dia_hora"),
    path("api/cohortes/", views.api_cohortes, name="api_cohortes"),
    path("api/ltv-clientes/", views.api_ltv, name="api_ltv"),
    path("api/repeat-rate/", views.api_repeat_rate, name="api_repeat_rate"),
    path("api/inventario-metricas/", views.api_inventario_metricas, name="api_inventario_metricas"),
    path("api/margen-servicios/", views.api_margen_servicios, name="api_margen_servicios"),
    path("api/funnel-citas/", views.api_funnel_citas, name="api_funnel_citas"),

    # Export
    path("export/citas.csv", views.export_citas_csv, name="export_citas_csv"),
    path("export/citas.xlsx", views.export_citas_xlsx, name="export_citas_xlsx"),
]
