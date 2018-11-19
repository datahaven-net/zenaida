# Generated by Django 2.1.2 on 2018-11-19 11:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('back', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contact',
            name='epp_id',
            field=models.CharField(blank=True, default=None, max_length=32, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='domain',
            name='epp_id',
            field=models.CharField(blank=True, default=None, max_length=32, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='registrar',
            name='epp_id',
            field=models.CharField(blank=True, default=None, max_length=32, unique=True),
        ),
    ]