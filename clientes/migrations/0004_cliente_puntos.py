""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("clientes", "0003_cliente_documento_cliente_es_empresa_cliente_notas_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="cliente",
            name="nivel",
            field=models.CharField(blank=True, max_length=30, verbose_name="Nivel fidelización"),
        ),
        migrations.AddField(
            model_name="cliente",
            name="puntos_saldo",
            field=models.PositiveIntegerField(default=0, verbose_name="Puntos disponibles"),
        ),
        migrations.AddIndex(
            model_name="cliente",
            index=models.Index(fields=["puntos_saldo"], name="clientes_clie_puntos_8a2c2d_idx"),
        ),
    ]
