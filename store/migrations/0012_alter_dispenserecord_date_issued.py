# Generated by Django 4.2.7 on 2025-01-16 18:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0011_alter_dispenserecord_date_issued_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dispenserecord',
            name='date_issued',
            field=models.DateField(null=True),
        ),
    ]
