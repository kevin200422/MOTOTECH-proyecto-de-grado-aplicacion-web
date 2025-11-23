"""
URL configuration for transacciones app.
"""
from __future__ import annotations

from django.urls import path

from . import views


app_name = 'transacciones'

urlpatterns = [
    path('', views.lista_transacciones, name='list'),
    path('nueva/', views.crear_transaccion, name='create'),
]