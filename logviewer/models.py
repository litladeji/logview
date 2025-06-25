from django.db import models

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


class TestStation(models.Model):
    station_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    calibration_date = models.DateField()

    def __str__(self):
        return f"{self.station_id} - {self.name}"
