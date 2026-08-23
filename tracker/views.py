from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.utils import timezone
from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from django.http import HttpResponse
from tracker.tasks import dispatch_device_classification_jobs
from datetime import timedelta
from .serializers import BrowsingSessionSerializer
from .models import BrowsingSession
import logging

logger = logging.getLogger('tracker')

class SessionIngestionView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = BrowsingSessionSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Malformed payload rejected: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        
        session_id = data.pop('id')
        if not session_id:
            return Response({"error": "Missing session ID"}, status=status.HTTP_400_BAD_REQUEST)

        active_duration = data.get('active_duration_seconds', 0)
        metadata = data.get('metadata', {})
        
        granular = metadata.pop('granular_engagement', {})
        
        clicks = data.get('clicks', granular.get('clicks', 0))
        scrolls = data.get('scrolls', granular.get('scrolls', 0))
        keystrokes = data.get('keystrokes', granular.get('keystrokes', 0))

        weighted_score = (keystrokes * 3) + (clicks * 2) + (scrolls * 1)
        
        ipm = 0
        if active_duration > 0:
            ipm = (weighted_score / active_duration) * 60
            
        normalized_engagement = min(int(ipm), 300)

        session, created = BrowsingSession.objects.update_or_create(
            id=session_id,
            defaults={
                'device_id': data.get('device_id', 'unknown_device'),
                'url': data.get('url'),
                'domain': data.get('domain'),
                'start_time': data.get('start_time'),
                'end_time': data.get('end_time'),
                'active_duration_seconds': active_duration,
                'background_audio_seconds': data.get('background_audio_seconds', 0),
                'clicks': clicks,
                'scrolls': scrolls,
                'keystrokes': keystrokes,
                'engagement_score': normalized_engagement,
                'metadata': metadata
            }
        )

        action = "Created new" if created else "Updated existing"
        logger.info(f"{action} session {session.id} for {session.domain} (Score: {normalized_engagement})")
        
        return Response(
            {"message": "Session recorded", "session_id": session.id, "created": created}, 
            status=status.HTTP_200_OK
        )

class TimelineListView(generics.ListAPIView):
    """
    Returns classified browsing sessions for the dashboard timeline.
    Defaults to the last 24 hours of activity.
    """
    serializer_class = BrowsingSessionSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = BrowsingSession.objects.filter(ai_intent__isnull=False)

        device_id = self.request.query_params.get('device_id')
        if device_id:
            queryset = queryset.filter(device_id=device_id)

        try:
            hours = int(self.request.query_params.get('hours', 24))
        except ValueError:
            hours = 24

        time_window = timezone.now() - timedelta(hours=hours)
        
        return queryset.filter(start_time__gte=time_window).order_by('start_time')
        

@api_view(['GET'])
@permission_classes([AllowAny])
def trigger_classification_cron(request):
    """Triggered every 5 minutes by external cron to dispatch workflow classification jobs."""
    result = dispatch_device_classification_jobs.delay()
    return Response(
        {"message": "Classification dispatched", "task_id": str(result.id)},
        status=status.HTTP_200_OK
    )


def health_check(request):
    return HttpResponse("OK")