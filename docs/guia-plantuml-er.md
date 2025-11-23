# Guía para pedir a ChatGPT un diagrama ER en PlantUML

Esta guía explica qué información necesita ChatGPT (u otro asistente compatible) para producir el diagrama entidad-relación (ER) del proyecto **Taller Mecánico** usando **PlantUML**. Síguela cada vez que modifiques los modelos para mantener la documentación actualizada.

## 1. Objetivo y alcance

- Documentar el modelo de datos de la base SQLite/Django mediante PlantUML.
- Reutilizar la misma estructura de prompt de forma consistente.
- Facilitar que cualquier miembro del equipo genere una imagen actualizada del ER sin memorizar la sintaxis de PlantUML.

## 2. Resumen de entidades actuales

| App | Tabla principal | Campos clave | Relaciones |
| --- | --- | --- | --- |
| `clientes` | `Cliente` | `nombre`, `documento`, `telefono`, `email`, `origen`, `es_empresa`, `puntos_saldo`, `nivel` | 1:N `Vehiculo`, 1:N `Cita`, 1:N `HistorialPuntos` |
| `vehiculos` | `Vehiculo` | `placa`, `marca`, `modelo`, `anio`, `color` | N:1 `Cliente`, 1:N `Cita` |
| `servicios` | `Servicio` | `nombre`, `descripcion`, `duracion_minutos`, `costo`, `precio`, `activo` | 1:N `Cita`, M:N `ConfigPuntos` (exclusiones) |
| `citas` | `Cita` | `titulo`, `descripcion`, `fecha_inicio`, `fecha_fin`, `estado` | N:1 `Cliente`, N:1 `Vehiculo`, N:1 `Servicio`, 1:N `Transaccion` |
| `transacciones` | `Transaccion` | `subtotal`, `monto`, `descuento_puntos`, `puntos_redimidos`, `puntos_otorgados`, `metodo_pago`, `fecha` | N:1 `Cita` |
| `inventario` | `Repuesto` | `codigo`, `nombre`, `categoria`, `stock`, `costo_unitario`, `precio_venta`, `tiempo_reposicion_dias`, `activo` | 1:N `MovimientoInventario` |
|  | `MovimientoInventario` | `tipo`, `cantidad`, `costo_unitario`, `referencia`, `notas`, `fecha` | N:1 `Repuesto`, N:1 `auth.User` |
| `fidelizacion` | `ConfigPuntos` | `puntos_por_monto`, `monto_base_cop`, `puntos_equivalencia`, `valor_redencion_cop`, `puntos_max_por_factura`, `exclusiones_servicios`, `exclusiones_categorias`, `niveles_config` | M:N `Servicio` |
|  | `HistorialPuntos` | `fecha`, `tipo`, `monto_pesos`, `puntos_ganados`, `puntos_usados`, `saldo_resultante`, `referencia`, `motivo`, `metadata` | N:1 `Cliente`, N:1 `auth.User`, referencia textual a `Transaccion` |
| `auth` | `User` (core Django) | `username`, `email`, etc. | Referenciado por `MovimientoInventario` y `HistorialPuntos` |

Adecua esta tabla cuando agregues nuevos campos o modelos.

## 3. Pasos previos a pedir el diagrama

1. Revisa los archivos `models.py` de cada app y confirma campos y relaciones.
2. Anota cambios recientes (por ejemplo, nuevas ForeignKey o tablas intermedias).
3. Copia la tabla de arriba y actualízala si es necesario.
4. Decide si quieres que el diagrama muestre atributos mínimos (solo claves) o una lista extendida.

## 4. Plantilla de prompt para ChatGPT

Usa el siguiente bloque como plantilla. Sustituye los campos marcados con `<>` y pega la tabla (o una versión abreviada) en el mensaje.

````markdown
Necesito que generes un diagrama entidad-relación en **PlantUML** para mi proyecto Django. Sigue las reglas:

1. Usa `@startuml` / `@enduml` y el estereotipo `entity`.
2. Incluye cada entidad listada con los atributos principales (marca claves primarias con `*` y foráneas con `+`).
3. Dibuja las relaciones mostrando la cardinalidad (por ejemplo `Cliente ||--o{ Vehiculo`).
4. Añade notas breves si hay relaciones indirectas (por ejemplo, referencias mediante texto).

Información del modelo:

| Entidad | Clave primaria | Campos relevantes | Relaciones |
| --- | --- | --- | --- |
| Cliente | id | nombre, documento (único), telefono, email, origen, es_empresa, puntos_saldo, nivel, ultimo_contacto | 1:N Vehiculo, 1:N Cita, 1:N HistorialPuntos |
| Vehiculo | id | placa (única), marca, modelo, anio, color | N:1 Cliente, 1:N Cita |
| Servicio | id | nombre, duracion_minutos, costo, precio, activo | 1:N Cita, M:N ConfigPuntos (excluye servicios) |
| Cita | id | titulo, fecha_inicio, fecha_fin, estado | N:1 Cliente, N:1 Vehiculo, N:1 Servicio, 1:N Transaccion |
| Transaccion | id | subtotal, monto, descuento_puntos, puntos_redimidos, puntos_otorgados, metodo_pago, fecha | N:1 Cita |
| Repuesto | id | codigo (único), nombre, categoria, stock, costo_unitario, precio_venta, activo | 1:N MovimientoInventario |
| MovimientoInventario | id | tipo, cantidad, costo_unitario, referencia, fecha, notas | N:1 Repuesto, N:1 User |
| ConfigPuntos | id | puntos_por_monto, monto_base_cop, puntos_equivalencia, valor_redencion_cop, puntos_max_por_factura, exclusiones_servicios, exclusiones_categorias, niveles_config | M:N Servicio (exclusiones) |
| HistorialPuntos | id | fecha, tipo, monto_pesos, puntos_ganados, puntos_usados, saldo_resultante, referencia, motivo, metadata | N:1 Cliente, N:1 User, referencia textual a Transaccion |
| User | id | username, email | Referenciado por MovimientoInventario y HistorialPuntos |

Devuélveme solo el código PlantUML.
````

Guarda esta plantilla en tu gestor de snippets para reutilizarla.

## 5. Ejemplo de respuesta esperada

````plantuml
@startuml
hide circle

entity Cliente {
  *id : AutoField
  nombre
  documento <<unique>>
  telefono
  email
  origen
  es_empresa : bool
  puntos_saldo
  nivel
}

entity Vehiculo {
  *id
  +cliente_id
  placa <<unique>>
  marca
  modelo
  anio
}

entity Servicio {
  *id
  nombre
  duracion_minutos
  costo
  precio
  activo
}

entity Cita {
  *id
  +cliente_id
  +vehiculo_id
  +servicio_id
  titulo
  fecha_inicio
  fecha_fin
  estado
}

entity Transaccion {
  *id
  +cita_id
  subtotal
  monto
  descuento_puntos
  puntos_redimidos
  puntos_otorgados
  metodo_pago
  fecha
}

entity Repuesto {
  *id
  codigo <<unique>>
  nombre
  categoria
  stock
  costo_unitario
  precio_venta
  activo
}

entity MovimientoInventario {
  *id
  +repuesto_id
  +user_id
  tipo
  cantidad
  costo_unitario
  referencia
  fecha
}

entity ConfigPuntos {
  *id
  puntos_por_monto
  monto_base_cop
  puntos_equivalencia
  valor_redencion_cop
  puntos_max_por_factura
}

entity HistorialPuntos {
  *id
  +cliente_id
  +user_id
  fecha
  tipo
  monto_pesos
  puntos_ganados
  puntos_usados
  saldo_resultante
  referencia
}

entity User {
  *id
  username
  email
}

Cliente ||--o{ Vehiculo : posee
Cliente ||--o{ Cita : agenda
Vehiculo ||--o{ Cita : usa
Servicio ||--o{ Cita : presta
Cita ||--o{ Transaccion : liquida
Cliente ||--o{ HistorialPuntos : registra
User ||--o{ HistorialPuntos : aprueba
User ||--o{ MovimientoInventario : ejecuta
Repuesto ||--o{ MovimientoInventario : mueve
ConfigPuntos }o--o{ Servicio : excluye
Transaccion ||..|| HistorialPuntos : "referencia textual"
@enduml
````

Usa la respuesta como entrada en [PlantUML Online](https://www.plantuml.com/plantuml) o en la extensión de tu editor (VS Code, JetBrains, etc.) para renderizar la imagen.

## 6. Buenas prácticas

- **Versiona** el código PlantUML final exportándolo a `docs/diagramas/bd-er.puml` o similar.
- **Adjunta** la imagen renderizada (`.png` o `.svg`) en `static/diagramas/`.
- **Repite** el proceso tras cada cambio en `models.py`.
- **Anota** en el README la fecha de la última actualización del diagrama.

Con esta guía podrás generar rápidamente instrucciones claras para ChatGPT y mantener sincronizada la documentación del modelo de datos.
