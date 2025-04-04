# Generated by Django 5.1.5 on 2025-02-20 11:11

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('erp_main', '0011_delete_standardprice'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='organization',
            name='contracts',
        ),
        migrations.CreateModel(
            name='Contract',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ('file', models.FileField(upload_to='contracts/')),
                ('days', models.IntegerField(blank=True, null=True)),
                ('legal_entity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contracts', to='erp_main.legalentity')),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contracts', to='erp_main.organization')),
            ],
        ),
    ]
