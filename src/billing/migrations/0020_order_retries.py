# Generated by Django 3.2.5 on 2022-01-22 13:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0019_alter_orderitem_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='retries',
            field=models.IntegerField(default=0),
        ),
    ]
