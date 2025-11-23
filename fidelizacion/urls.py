from django.urls import path

from fidelizacion import views

app_name = 'fidelizacion'

urlpatterns = [
    path('clientes/<int:cliente_id>/', views.historial_cliente, name='historial_cliente'),
    path('clientes/<int:cliente_id>/ajustar/', views.ajustar_puntos, name='ajustar_cliente'),
    path('configuracion/', views.configuracion, name='configuracion'),
]
