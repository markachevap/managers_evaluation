from django.urls import path
from .views import (
    UserListView, UserCreateView, UserUpdateView, UserDetailView,
    CustomRoleListView, CustomRoleCreateView, CustomRoleUpdateView, CustomRoleDeleteView, CustomLoginView, UserAssignRoleView
)
from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from .views import CustomLoginView
from . import views

app_name = 'users'

auth_urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),

    path('logout/', auth_views.LogoutView.as_view(
        template_name='users/logout.html',
        next_page=reverse_lazy('login')
    ), name='logout'),

    # Восстановление пароля
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='users/password_reset_form.html',
        email_template_name='users/password_reset_email.html',
        subject_template_name='users/password_reset_subject.txt',
        success_url=reverse_lazy('users:password_reset_done')
    ), name='password_reset'),

    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='users/password_reset_done.html'
    ), name='password_reset_done'),

    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='users/password_reset_confirm.html',
        success_url=reverse_lazy('users:password_reset_complete')
    ), name='password_reset_confirm'),

    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='users/password_reset_complete.html'
    ), name='password_reset_complete'),
]

urlpatterns = [
# Управление пользователями
    path('', UserListView.as_view(), name='user-list'),
    path('create/', UserCreateView.as_view(), name='user-create'),
    path('<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('<int:pk>/update/', UserUpdateView.as_view(), name='user-update'),

    # Управление кастомными ролями
    path('<int:pk>/assign-role/', UserAssignRoleView.as_view(), name='assign-role'),
    path('roles/', CustomRoleListView.as_view(), name='role-list'),
    path('roles/create/', CustomRoleCreateView.as_view(), name='role-create'),
    path('roles/<int:pk>/update/', CustomRoleUpdateView.as_view(), name='role-update'),
    path('roles/<int:pk>/delete/', CustomRoleDeleteView.as_view(), name='role-delete'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('register/', views.register, name='register'),

    *auth_urlpatterns
]