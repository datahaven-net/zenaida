# Generated by Django 2.2.13 on 2020-07-01 18:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('back', '0026_auto_20200504_0830'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='automatic_renewal_enabled',
            field=models.BooleanField(default=True, help_text='Your domains will be automatically renewed 3 months before the expiration date, if you have enough funds. Account balance will be automatically deducted.', verbose_name='Automatically renew expiring domains'),
        ),
    ]