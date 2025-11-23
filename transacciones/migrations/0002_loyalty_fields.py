from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("transacciones", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="transaccion",
            name="puntos",
        ),
        migrations.AddField(
            model_name="transaccion",
            name="descuento_puntos",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="transaccion",
            name="puntos_otorgados",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="transaccion",
            name="puntos_redimidos",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="transaccion",
            name="subtotal",
            field=models.DecimalField(decimal_places=2, default=0, help_text="Subtotal antes de descuentos.", max_digits=10),
            preserve_default=False,
        ),
    ]
