from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('leader/', views.LeaderAnalyticsView.as_view(), name='leader-analytics'),
    path('manager/', views.ManagerAnalyticsView.as_view(), name='manager-analytics'),
    path('compare/', views.ComparisonAnalyticsView.as_view(), name='comparison-analytics'),
    path('manager/<int:manager_id>/', views.ManagerAnalyticsView.as_view(), name='manager-analytics')
]
