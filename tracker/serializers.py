# tracker/serializers.py
from rest_framework import serializers
from .models import BrowsingSession

class BrowsingSessionSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField()

    class Meta:
        model = BrowsingSession
        fields = [
            'id',
            'device_id',
            'url', 
            'domain', 
            'start_time', 
            'end_time', 
            'active_duration_seconds', 
            'background_audio_seconds', 
            'clicks',              
            'scrolls',             
            'keystrokes',          
            'engagement_score', 
            'metadata',
            'user_override_intent',
            'ai_intent'
        ]
        
        # This tells Django to ONLY use these for outgoing GET requests. 
        # Any incoming POST data containing these keys will be safely ignored.
        read_only_fields = [
            'ai_intent', 
            'user_override_intent', 
            'engagement_score',
            'clicks',
            'scrolls',
            'keystrokes'
        ]
