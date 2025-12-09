from django.db import models
from simple_history.models import HistoricalRecords


class TrackedModel(models.Model):
    """Базовая модель с отслеживанием истории"""

    history = HistoricalRecords(
        inherit=False,
        cascade_delete_history=True,
        excluded_fields=['created_at', 'updated_at'],
        history_change_reason_field=models.TextField(null=True, blank=True),
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """Автоматическое добавление причины при обновлении"""
        if self.pk and 'reason' not in kwargs:
            kwargs['reason'] = 'Автоматическое обновление'
        super().save(*args, **kwargs)