# Taller Mecánico – Sistema de Gestión y Análisis

Este proyecto implementa una aplicación web completa para la
administración integral de un taller mecánico en San&nbsp;Juan
**NEPOMUCENO**.  La solución fue desarrollada con
[Django](https://www.djangoproject.com/), un framework de Python para
aplicaciones web que proporciona una arquitectura robusta, un ORM
potente y un sistema de plantillas flexible.  Incluye módulos para
gestionar clientes, vehículos, servicios, inventario de repuestos,
citas, transacciones y un panel de *business&nbsp;intelligence* que
visualiza indicadores clave mediante gráficos.

## Requisitos previos

Para ejecutar el proyecto en tu equipo necesitarás:

* **Python 3.8 o superior**: Descárgalo desde [python.org](https://www.python.org/downloads/).
* **pip** (suele estar incluido con Python) para instalar dependencias.
* Opcional pero recomendable: **virtualenv** para crear entornos
  aislados.

## Instalación y puesta en marcha

Sigue estos pasos para poner en funcionamiento la aplicación en tu
máquina local:

1. **Clona o descomprime el proyecto**.  Copia la carpeta `taller_mecanico` en
   el lugar que desees en tu equipo.

2. **Crea un entorno virtual** (opcional pero recomendable) y actívalo:

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

3. **Instala las dependencias**.  Este proyecto utiliza únicamente
   Django, definido en `requirements.txt`.

   ```bash
   pip install -r requirements.txt
   ```

4. **Aplica las migraciones** para crear las tablas en la base de
   datos SQLite incluida por defecto:

   ```bash
   python manage.py migrate
   ```

5. **Crea un usuario administrador** para acceder al panel de
   administración de Django:

   ```bash
   python manage.py createsuperuser
   # sigue las instrucciones para establecer usuario y contraseña
   ```

6. **Inicia el servidor de desarrollo**:

   ```bash
   python manage.py runserver
   ```

7. Abre un navegador y visita [http://localhost:8000](http://localhost:8000).
   Verás la pantalla de inicio del sistema con las tarjetas de
   conteo y las próximas citas.  Desde la barra de navegación
   podrás acceder a cada módulo:

   * **Citas:** Lista y crea citas asociadas a clientes, vehículos y
     servicios.  El sistema calcula automáticamente la hora de
     finalización en función de la duración del servicio.
   * **Clientes:** Registra y administra la información de tus
     clientes, incluyendo contacto y dirección.
   * **Vehículos:** Gestiona los vehículos de tus clientes, con marca,
     modelo, año, placa y color.
   * **Servicios:** Define los servicios ofrecidos por el taller, su
     precio y duración.  Puedes activar o desactivar servicios según
     disponibilidad.
   * **Inventario:** Controla tus repuestos.  Cada repuesto lleva
     código, descripción, stock, stock mínimo y precio.  La interfaz
     permite añadir nuevos repuestos y ver su estado.
   * **Transacciones:** Registra los pagos de las citas completadas y
     gestiona puntos de fidelización.  Selecciona la cita, el monto,
     el método de pago y los puntos otorgados.
   * **Dashboard:** Visualiza métricas clave: distribución de citas por
     estado, servicios más solicitados, número total de clientes,
     vehículos, servicios y citas, además de un listado de próximas
     citas.

## Personalización

* **Base de datos**: Por defecto se usa SQLite (`db.sqlite3`).  Puedes
  cambiarla por PostgreSQL u otro motor modificando la sección
  `DATABASES` en `taller_mecanico/settings.py`.
* **Zona horaria**: Está configurada en `America/Bogota`.  Ajusta
  `TIME_ZONE` según tus necesidades.
* **Estilos**: El diseño utiliza un CSS simple alojado en
  `static/css/styles.css`.  Puedes modificarlo o reemplazarlo para
  adaptar la apariencia a la imagen corporativa del taller.

## Estructura del proyecto

```
taller_mecanico/
├── manage.py               # Script de administración de Django
├── db.sqlite3              # Base de datos local (creada después de migrar)
├── requirements.txt        # Dependencias del proyecto
├── README.md               # Este archivo
├── static/                 # Archivos estáticos globales (CSS)
│   └── css/styles.css
├── templates/              # Plantillas compartidas
│   └── base.html
├── taller_mecanico/        # Configuración del proyecto
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── __init__.py
├── clientes/
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   ├── urls.py
│   ├── apps.py
│   └── templates/clientes/
│       ├── list.html
│       └── form.html
├── vehiculos/ …            # Estructura similar para cada app
├── servicios/ …
├── inventario/ …
├── citas/ …
├── transacciones/ …
└── dashboard/
    ├── views.py
    ├── urls.py
    └── templates/dashboard/
        ├── home.html
        └── overview.html
```

## Funcionalidades destacadas

* **Gestión de clientes y vehículos:** Permite registrar clientes,
  vincularles vehículos y consultar su historial de citas y
  transacciones.
* **Agenda de citas con recordatorios:** Crea citas asociando cliente,
  vehículo y servicio.  Calcula automáticamente la hora de fin en
  función del servicio.  (Para enviar recordatorios por correo o
  WhatsApp sería necesario integrar bibliotecas externas y
  configurar un servicio de mensajería.)
* **Control de inventario:** Registra repuestos con stock y stock
  mínimo, facilitando la planificación de compras.  El modelo
  expone la propiedad `bajo_stock` para detectar artículos con
  existencias bajas.
* **Transacciones y fidelización:** Registra pagos de servicios,
  el método empleado y los puntos acumulados para programas de
  fidelización.
* **Panel de estadísticas (BI ligero):** Muestra un tablero con
  indicadores de citas por estado y servicios más solicitados.  Usa
  Chart.js vía CDN para dibujar gráficas de pastel y de barras.

## Siguientes pasos y mejoras

Esta base funcional cubre los requisitos principales del proyecto
planificado.  Algunas ampliaciones futuras podrían ser:

* Integrar envío de recordatorios por correo electrónico y WhatsApp
  utilizando Celery o `django-cron` para tareas periódicas.
* Implementar un sistema de autenticación más completo con roles de
  usuario (administrador, mecánico, recepcionista).
* Exponer API REST (con Django REST Framework) para integrar una
  aplicación móvil de clientes.
* Añadir predicción de demanda usando bibliotecas de análisis
  estadístico (por ejemplo, pandas, scikit-learn) en un módulo
  separado y mostrar los resultados en el dashboard.

¡Esperamos que esta aplicación sea de gran utilidad para tu taller!