# Generated by Django 2.2 on 2019-05-12 14:57

from django.db import migrations, models
import django.db.models.manager


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0011_auto_20190505_1645'),
    ]

    operations = [
        migrations.CreateModel(
            name='BTCPayInvoice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transaction_id', models.CharField(max_length=16, unique=True)),
                ('invoice_id', models.CharField(max_length=32, unique=True)),
                ('amount', models.FloatField()),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('finished_at', models.DateTimeField(blank=True, default=None, null=True)),
                ('status', models.CharField(choices=[('new', 'New'), ('paid', 'Paid'), ('confirmed', 'Confirmed'), ('complete', 'Complete'), ('expired', 'Expired'), ('invalid', 'Invalid')], default='started', max_length=16)),
            ],
            options={
                'base_manager_name': 'invoices',
                'default_manager_name': 'invoices',
            },
            managers=[
                ('invoices', django.db.models.manager.Manager()),
            ],
        ),
    ]