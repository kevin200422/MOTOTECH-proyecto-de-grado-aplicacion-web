from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("servicios", "0002_servicio_costo_alter_servicio_duracion_minutos"),
        ("clientes", "0003_cliente_documento_cliente_es_empresa_cliente_notas_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ConfigPuntos",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "puntos_por_monto",
                    models.PositiveIntegerField(
                        default=1,
                        help_text="Cantidad de puntos otorgados cuando el subtotal alcanza el monto_base_cop.",
                    ),
                ),
                (
                    "monto_base_cop",
                    models.PositiveIntegerField(
                        default=1000,
                        help_text="Monto en COP requerido para otorgar puntos (antes de impuestos/propinas).",
                    ),
                ),
                (
                    "puntos_equivalencia",
                    models.PositiveIntegerField(
                        default=100,
                        help_text="Cantidad de puntos requeridos para redimir valor_redencion_cop pesos.",
                    ),
                ),
                (
                    "valor_redencion_cop",
                    models.PositiveIntegerField(
                        default=1000,
                        help_text="Valor en COP descontado cuando se redimen puntos_equivalencia puntos.",
                    ),
                ),
                (
                    "puntos_max_por_factura",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Tope de puntos otorgados por factura (0 = sin tope).",
                    ),
                ),
                (
                    "exclusiones_categorias",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Lista de categorÃ­as (texto) excluidas del programa.",
                    ),
                ),
                (
                    "niveles_config",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="ConfiguraciÃ³n opcional de niveles {'Bronce': 0, 'Plata': 5000, ...}.",
                    ),
                ),
                ("actualizado", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "configuraciÃ³n de puntos",
                "verbose_name_plural": "configuraciones de puntos",
            },
        ),
        migrations.CreateModel(
            name="HistorialPuntos",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fecha", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                (
                    "tipo",
                    models.CharField(
                        choices=[
                            ("gana", "Gana puntos"),
                            ("usa", "Usa puntos"),
                            ("bono", "BonificaciÃ³n"),
                            ("ajuste", "Ajuste manual"),
                            ("reversa", "ReversiÃ³n"),
                        ],
                        max_length=12,
                    ),
                ),
                ("monto_pesos", models.DecimalField(decimal_places=2, default="0.00", max_digits=12)),
                ("puntos_ganados", models.IntegerField(default=0)),
                ("puntos_usados", models.IntegerField(default=0)),
                ("saldo_resultante", models.PositiveIntegerField()),
                ("referencia", models.CharField(blank=True, max_length=120)),
                ("motivo", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="movimientos_puntos",
                        to="clientes.cliente",
                    ),
                ),
                (
                    "usuario_admin",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="historial_puntos_admin",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "movimiento de puntos",
                "verbose_name_plural": "movimientos de puntos",
                "ordering": ["-fecha"],
            },
        ),
        migrations.AddField(
            model_name="configpuntos",
            name="exclusiones_servicios",
            field=models.ManyToManyField(
                blank=True,
                help_text="Servicios que no generan puntos.",
                related_name="excluido_fidelizacion",
                to="servicios.servicio",
            ),
        ),
        migrations.AddIndex(
            model_name="historialpuntos",
            index=models.Index(fields=["cliente", "fecha"], name="historial_cliente_fecha_idx"),
        ),
        migrations.AddIndex(
            model_name="historialpuntos",
            index=models.Index(fields=["referencia"], name="historial_referencia_idx"),
        ),
        migrations.AddIndex(
            model_name="historialpuntos",
            index=models.Index(fields=["tipo"], name="historial_tipo_idx"),
        ),
    ]

