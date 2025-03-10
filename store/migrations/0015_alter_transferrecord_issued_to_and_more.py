# Generated by Django 4.2.7 on 2025-01-27 18:11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0014_alter_transferrecord_unit'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transferrecord',
            name='issued_to',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='receiving_unit', to='store.unit'),
        ),
        migrations.AlterField(
            model_name='transferrecord',
            name='unit',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transfer_unit', to='store.unit'),
        ),
    ]
