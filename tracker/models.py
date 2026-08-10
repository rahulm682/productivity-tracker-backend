from django.db import models
from pgvector.django import VectorField, HnswIndex

class BrowsingSession(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    
    device_id = models.CharField(max_length=255, db_index=True)
    
    url = models.TextField()
    domain = models.CharField(max_length=255, db_index=True)
    
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    active_duration_seconds = models.IntegerField(default=0)
    background_audio_seconds = models.IntegerField(default=0)
    
    clicks = models.IntegerField(default=0)
    scrolls = models.IntegerField(default=0)
    keystrokes = models.IntegerField(default=0)
    
    engagement_score = models.IntegerField(default=0)
    
    metadata = models.JSONField(default=dict, blank=True)
    
    ai_intent = models.CharField(max_length=100, null=True, blank=True)
    user_override_intent = models.CharField(max_length=100, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.domain} ({self.active_duration_seconds}s active, {self.background_audio_seconds}s bg) - {self.device_id}"


class DomainSemanticCache(models.Model):
    domain_or_url = models.CharField(max_length=512, primary_key=True)
    cached_intent = models.CharField(max_length=100)
    
    embedding = VectorField(dimensions=1536, help_text="Vector embedding of the page metadata")
    
    last_verified_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            HnswIndex(
                name='embedding_hnsw_idx',
                fields=['embedding'],
                m=16,
                ef_construction=64,
                opclasses=['vector_l2_ops']
            )
        ]

    def __str__(self):
        return f"{self.domain_or_url} -> {self.cached_intent}"
