# Generated by Django 4.1.13 on 2024-09-16 10:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('installation', '0006_alter_vehicleinstallation_user_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vehicleinstallation',
            name='user_type',
            field=models.CharField(default='Installed User', max_length=25),
        ),
    ]
