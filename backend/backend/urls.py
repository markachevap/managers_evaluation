from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from users import views as user_views  # Импортируем кастомные views, если они есть

urlpatterns = [
                  path('admin/', admin.site.urls),
                  path('evaluations/', include('evaluations.urls', namespace='evaluations')),
                  path('analytics/', include('analytics.urls')),

                  # Аутентификация
                  path('accounts/register/', user_views.register, name='register'),
                  path('accounts/login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
                  path('accounts/logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

                  # URL для сброса пароля
                  path('accounts/password_reset/',
                       auth_views.PasswordResetView.as_view(template_name='users/password_reset.html'),
                       name='password_reset'),
                  path('accounts/password_reset/done/',
                       auth_views.PasswordResetDoneView.as_view(template_name='users/password_reset_done.html'),
                       name='password_reset_done'),
                  path('accounts/reset/<uidb64>/<token>/',
                       auth_views.PasswordResetConfirmView.as_view(template_name='users/password_reset_confirm.html'),
                       name='password_reset_confirm'),
                  path('accounts/reset/done/',
                       auth_views.PasswordResetCompleteView.as_view(template_name='users/password_reset_complete.html'),
                       name='password_reset_complete'),

                  path('accounts/', include('users.urls', namespace='users')),
                  path('', include('core.urls')),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)