# vehiculos/urls.py
from django.urls import path
from . import views

app_name = "vehiculos"

urlpatterns = [
    path("", views.VehiculoListView.as_view(), name="list"),
    path("nuevo/", views.VehiculoCreateView.as_view(), name="create"),
    path("<int:pk>/", views.VehiculoDetailView.as_view(), name="detail"),   # <— ESTA LÍNEA
    path("<int:pk>/editar/", views.VehiculoUpdateView.as_view(), name="update"),
    path("<int:pk>/eliminar/", views.VehiculoDeleteView.as_view(), name="delete"),
]
