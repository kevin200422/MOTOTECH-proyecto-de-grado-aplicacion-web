"""
WSGI config for the Taller Mecánico project.

This file exposes the WSGI callable as a module-level variable named
``application``. It is used by Django's deployment scripts and by
WSGI servers such as Gunicorn or uWSGI in production environments.
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'taller_mecanico.settings')

application = get_wsgi_application()