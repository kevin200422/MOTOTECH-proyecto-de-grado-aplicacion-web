"""
Application configuration for the clientes app.

This module defines the default configuration for the clientes app. It
is used by Django to configure and register the application at
startup.
"""
from django.apps import AppConfig


class ClientesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'clientes'
    verbose_name = 'Clientes'