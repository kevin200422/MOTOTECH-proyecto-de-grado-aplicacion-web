# -*- coding: utf-8 -*-
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),

    # Auth (login/logout/password reset) — corrige NoReverseMatch de 'logout'
    path("accounts/", include("django.contrib.auth.urls")),

    # Apps
    path("clientes/", include(("clientes.urls", "clientes"), namespace="clientes")),
    path("vehiculos/", include(("vehiculos.urls", "vehiculos"), namespace="vehiculos")),
    path("servicios/", include(("servicios.urls", "servicios"), namespace="servicios")),
    path("inventario/", include(("inventario.urls", "inventario"), namespace="inventario")),
    path("citas/", include(("citas.urls", "citas"), namespace="citas")),
    path("transacciones/", include(("transacciones.urls", "transacciones"), namespace="transacciones")),
    path("dashboard/", include(("dashboard.urls", "dashboard"), namespace="dashboard")),
    path("fidelizacion/", include(("fidelizacion.urls", "fidelizacion"), namespace="fidelizacion")),

    # raíz => dashboard
    path("", RedirectView.as_view(pattern_name="dashboard:overview", permanent=False)),
]
