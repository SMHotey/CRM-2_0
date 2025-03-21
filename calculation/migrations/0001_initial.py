# Generated by Django 5.1.5 on 2025-02-10 08:17

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='StandardPrice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('door_1', models.JSONField()),
                ('door_2', models.JSONField()),
                ('wide_door_1', models.JSONField()),
                ('hatch_1', models.JSONField()),
                ('wide_hatch_1', models.JSONField()),
                ('not_standard', models.JSONField()),
                ('gate', models.JSONField()),
                ('wide_gate', models.JSONField()),
                ('transom', models.JSONField()),
                ('dobor', models.JSONField()),
                ('lock', models.JSONField()),
                ('handle', models.JSONField()),
                ('c_m', models.JSONField()),
                ('door_closer', models.JSONField()),
                ('metal', models.JSONField()),
                ('ral', models.JSONField()),
                ('vent_grate', models.JSONField()),
                ('plate', models.JSONField()),
                ('glass', models.JSONField()),
            ],
        ),
    ]
