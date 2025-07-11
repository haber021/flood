# Generated by Django 5.2 on 2025-05-04 07:23

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_municipality_barangay_municipality'),
    ]

    operations = [
        migrations.AddField(
            model_name='sensor',
            name='barangay',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sensors', to='core.barangay'),
        ),
        migrations.AddField(
            model_name='sensor',
            name='municipality',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sensors', to='core.municipality'),
        ),
    ]
