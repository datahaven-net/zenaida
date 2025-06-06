# Generated by Django 3.2.25 on 2025-05-22 18:26

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0021_alter_orderitem_status'),
        ('back', '0037_alter_domain_auto_renew_enabled'),
    ]

    operations = [
        migrations.AddField(
            model_name='backendrenew',
            name='restore_order',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='restore_renewals', to='billing.order'),
        ),
    ]
