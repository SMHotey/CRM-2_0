# Generated by Django 5.1 on 2025-01-16 07:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('erp_main', '0008_remove_order_comment_changes_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='internal_order_number',
        ),
        migrations.AlterField(
            model_name='orderchangehistory',
            name='order_file',
            field=models.FileField(upload_to='uploads/'),
        ),
    ]
