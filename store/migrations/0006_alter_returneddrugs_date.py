# Generated by Django 4.2.7 on 2025-01-11 13:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0005_remove_drugrequest_category_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='returneddrugs',
            name='date',
            field=models.DateField(auto_now=True, null=True),
        ),
    ]
