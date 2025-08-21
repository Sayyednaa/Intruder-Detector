# surveillance/admin.py
from django.contrib import admin
from .models import Device, IntrusionEvent, LastFrame

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'last_seen')


@admin.register(IntrusionEvent)
class IntrusionEventAdmin(admin.ModelAdmin):
    list_display = ('device', 'timestamp')  # removed kind, score
    list_filter = ('timestamp',)  # removed kind


from django.contrib import admin
from .models import LastFrame

@admin.register(LastFrame)
class LastFrameAdmin(admin.ModelAdmin):
    list_display = ("id", "device", "created_at", "updated_at", "width", "height", "fps")