from django.urls import path
from .views import (
    EvaluationCreateView, EvaluationUpdateView, EvaluationDetailView, EvaluationListView, EvaluationDeleteView, 
    ManagerDashboardView, LeaderDashboardView, ComparisonView, ManagerStatsView, BulkEvaluationCreateView
)

app_name = 'evaluations'

urlpatterns = [
    # Управление оценками
    path('', EvaluationListView.as_view(), name='evaluation-list'),
    path('create/', EvaluationCreateView.as_view(), name='evaluation-create'),
    path('<int:pk>/', EvaluationDetailView.as_view(), name='evaluation-detail'),
    path('<int:pk>/update/', EvaluationUpdateView.as_view(), name='evaluation-update'),
    path('<int:pk>/delete/', EvaluationDeleteView.as_view(), name='evaluation-delete'),

    # Дашборды
    path('dashboard/manager/', ManagerDashboardView.as_view(), name='manager-dashboard'),
    path('dashboard/leader/', LeaderDashboardView.as_view(), name='leader-dashboard'),
    path('compare/', ComparisonView.as_view(), name='compare-managers'),
    path('evaluations/bulk-create/', BulkEvaluationCreateView.as_view(), name='bulk-evaluation-create'),
    path('stats/<int:pk>/', ManagerStatsView.as_view(), name='manager-stats'),
]
