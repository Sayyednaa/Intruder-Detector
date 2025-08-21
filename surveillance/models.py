import uuid
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

def generate_token():
    return uuid.uuid4().hex

class Device(models.Model):
    name = models.CharField(max_length=100)
    token = models.CharField(max_length=64, unique=True, default=generate_token)
    is_active = models.BooleanField(default=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    motion_sensitivity = models.FloatField(default=0.5, help_text="0–1 sensitivity threshold")

    # Multi-user support
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name


class IntrusionEvent(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    snapshot = models.ImageField(upload_to="intrusions/")
    kind = models.CharField(max_length=50)  # e.g., "human", "child"
    score = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    # Multi-user support
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.kind} detected on {self.device} at {self.timestamp}"


class LastFrame(models.Model):
    device = models.OneToOneField(Device, on_delete=models.CASCADE, related_name="last_frame")
    frame = models.ImageField(upload_to="frames/")
    width = models.IntegerField(default=0)
    height = models.IntegerField(default=0)
    fps = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Multi-user support
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
