from django.urls import path
from .views import LeaderAnalyticsView, ManagerAnalyticsView, ComparisonAnalyticsView

app_name = 'analytics'

urlpatterns = [
    path('leader/', LeaderAnalyticsView.as_view(), name='leader-analytics'),
    path('manager/', ManagerAnalyticsView.as_view(), name='manager-analytics'),
    path('compare/', ComparisonAnalyticsView.as_view(), name='comparison-analytics'),
]