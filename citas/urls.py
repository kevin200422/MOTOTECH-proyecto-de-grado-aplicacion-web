# citas/urls.py
from django.urls import path
from . import views

app_name = "citas"

urlpatterns = [
    path("", views.CitaListView.as_view(), name="list"),
    path("nueva/", views.CitaCreateView.as_view(), name="create"),
    path("<int:pk>/", views.CitaDetailView.as_view(), name="detail"),
    path("<int:pk>/editar/", views.CitaUpdateView.as_view(), name="update"),
    path("<int:pk>/eliminar/", views.CitaDeleteView.as_view(), name="delete"),
    path("export/", views.citas_export_csv, name="export"),
    path("api/vehiculos-por-cliente/", views.api_vehiculos_por_cliente, name="api_vehiculos"),
    path("calendar.json", views.calendar_json, name="calendar_json"),
    path("ics/<int:pk>/", views.cita_ics, name="ics"),
]
