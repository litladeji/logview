from django.db import models
from django import forms
from djongo import models as djongo_models
from djongo.models import CharField, EmbeddedField, ArrayField, ObjectIdField, IntegerField, DjongoManager

LOCATION_LENGTH = 100
COMMENT_LENGTH = 1000

# Create your models here.
class LogEntry(models.Model):
    station_id = models.CharField(max_length=50)
    timestamp = models.DateTimeField()
    metrics = models.JSONField()
    result = models.CharField(max_length=10)
    filename = models.CharField(max_length=200, unique=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.station_id} - {self.timestamp} - {self.result}"