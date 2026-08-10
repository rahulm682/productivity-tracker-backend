from django.contrib import admin
from .models import BrowsingSession


@admin.register(BrowsingSession)
class BrowsingSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "domain",
        "device_id",
        "active_duration_seconds",
        "background_audio_seconds",
        "engagement_score",
        "ai_intent",
        "user_override_intent",
        "start_time",
        "end_time",
        "created_at",
    )

    search_fields = (
        "device_id",
        "domain",
        "url",
        "ai_intent",
        "user_override_intent",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = ("-start_time",)
