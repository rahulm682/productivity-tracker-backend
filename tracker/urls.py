from django.urls import path
from .views import SessionIngestionView, TimelineListView

urlpatterns = [
    path('sessions/', SessionIngestionView.as_view(), name='session-ingest'),
    path('sessions/timeline/', TimelineListView.as_view(), name='session-timeline'),
]
