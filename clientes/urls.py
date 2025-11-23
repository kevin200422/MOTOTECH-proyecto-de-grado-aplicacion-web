from __future__ import annotations

from django.urls import path

from .views import (
    ClienteCreateView,
    ClienteDeleteView,
    ClienteDetailView,
    ClienteExportCSVView,
    ClienteListView,
    ClienteTouchView,
    ClienteUpdateView,
)

app_name = "clientes"

urlpatterns = [
    path("", ClienteListView.as_view(), name="list"),
    path("nuevo/", ClienteCreateView.as_view(), name="create"),
    path("exportar/", ClienteExportCSVView.as_view(), name="export"),
    path("<int:pk>/", ClienteDetailView.as_view(), name="detail"),
    path("<int:pk>/editar/", ClienteUpdateView.as_view(), name="edit"),
    path("<int:pk>/actualizar/", ClienteUpdateView.as_view(), name="update"),
    path("<int:pk>/eliminar/", ClienteDeleteView.as_view(), name="delete"),
    path("<int:pk>/contacto/", ClienteTouchView.as_view(), name="touch"),
]
