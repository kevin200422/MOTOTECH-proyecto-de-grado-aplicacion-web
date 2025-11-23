from django.urls import path

from .views import (
    InventarioCreateView,
    InventarioDeleteView,
    InventarioDetailView,
    InventarioListView,
    InventarioUpdateView,
    MovimientoInventarioCreateView,
)

app_name = "inventario"

urlpatterns = [
    path("", InventarioListView.as_view(), name="list"),
    path("nuevo/", InventarioCreateView.as_view(), name="create"),
    path("<int:pk>/", InventarioDetailView.as_view(), name="detail"),
    path("<int:pk>/editar/", InventarioUpdateView.as_view(), name="update"),
    path("<int:pk>/eliminar/", InventarioDeleteView.as_view(), name="delete"),
    path("<int:pk>/movimientos/nuevo/", MovimientoInventarioCreateView.as_view(), name="movement_create"),
]
