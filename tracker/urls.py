from django.urls import path
from .views import SessionIngestionView, TimelineListView, trigger_classification_cron

urlpatterns = [
    path('sessions/', SessionIngestionView.as_view(), name='session-ingest'),
    path('sessions/timeline/', TimelineListView.as_view(), name='session-timeline'),
    path('sessions/cron-trigger/', trigger_classification_cron, name='cron-trigger'),
]
