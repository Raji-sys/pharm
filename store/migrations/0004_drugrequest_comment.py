# Generated by Django 4.2.7 on 2025-01-11 00:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0003_drugrequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='drugrequest',
            name='comment',
            field=models.CharField(blank=True, max_length=1000, null=True),
        ),
    ]
