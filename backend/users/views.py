from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from .models import User, CustomRole
from .forms import UserCreateForm, CustomRoleForm, AssignRoleForm
from evaluations.models import ManagerEvaluation
from django.contrib.auth.views import LoginView
from .forms import EmailAuthForm
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Window, F
from django.db.models.functions import FirstValue
from django.shortcuts import render, redirect
from .forms import RegisterForm
from .models import User
from django.contrib.auth import login


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save() #user = form.save(commit=False)
            user.system_role = User.SYSTEM_LEADER  # Устанавливаем роль по умолчанию
            user.save()

            # Автоматический вход после регистрации
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.get_full_name()}!')
            return redirect('home')  # Замените 'home' на ваш URL главной страницы
    else:
        form = RegisterForm()

    return render(request, 'users/register.html', {'form': form})
managers = User.objects.annotate(
    last_score=Window(
        expression=FirstValue('evaluations__total_score'),
        partition_by=['id'],
        order_by=F('evaluations__evaluation_date').desc()
    )
)

class CustomLoginView(LoginView):
    form_class = EmailAuthForm
    template_name = 'users/login.html'
    success_url = reverse_lazy('users:user-list')

class LeaderRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.system_role == User.SYSTEM_LEADER

class UserListView(LeaderRequiredMixin, ListView):
    model = User
    template_name = 'users/user_list.html'
    context_object_name = 'users'

    def get_queryset(self):
        return User.objects.filter(system_role=User.SYSTEM_MANAGER).order_by('last_name')

class UserCreateView(LeaderRequiredMixin, CreateView):
    model = User
    form_class = UserCreateForm
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('users:user-list')

    def form_valid(self, form):
        form.instance.system_role = User.SYSTEM_MANAGER
        return super().form_valid(form)

class UserUpdateView(LeaderRequiredMixin, UpdateView):
    model = User
    form_class = UserCreateForm
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('users:user-list')


class UserDetailView(LeaderRequiredMixin, DetailView):
    model = User
    template_name = 'users/user_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object.system_role == User.SYSTEM_MANAGER:
            context['evaluations'] = ManagerEvaluation.objects.filter(
                manager=self.object
            ).order_by('-evaluation_date')
        else:
            context['evaluations'] = None
        context['user_evaluations'] = self.object.evaluations.order_by('-evaluation_date')[:5]
        return context

    def get_queryset(self):
        # Руководители могут просматривать всех пользователей
        return User.objects.all()

class CustomRoleListView(LeaderRequiredMixin, ListView):
    model = CustomRole
    template_name = 'users/role_list.html'
    context_object_name = 'roles'

    def get_queryset(self):
        return CustomRole.objects.filter(created_by=self.request.user)

class CustomRoleCreateView(LeaderRequiredMixin, CreateView):
    model = CustomRole
    form_class = CustomRoleForm
    template_name = 'users/role_form.html'
    success_url = reverse_lazy('users:role-list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

class CustomRoleUpdateView(LeaderRequiredMixin, UpdateView):
    model = CustomRole
    form_class = CustomRoleForm
    template_name = 'users/role_form.html'
    success_url = reverse_lazy('users:role-list')

    def get_queryset(self):
        return CustomRole.objects.filter(created_by=self.request.user)

class CustomRoleDeleteView(LeaderRequiredMixin, DeleteView):
    model = CustomRole
    template_name = 'users/role_confirm_delete.html'
    success_url = reverse_lazy('users:role-list')

    def get_queryset(self):
        return CustomRole.objects.filter(created_by=self.request.user)

class UserAssignRoleView(LeaderRequiredMixin, UpdateView):
    model = User
    form_class = AssignRoleForm
    template_name = 'users/assign_role.html'
    success_url = reverse_lazy('users:user-list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['leader'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _('Role assigned successfully!'))
        return super().form_valid(form)

    def form_invalid(self, form):
         messages.error(self.request, _('Failed to assign role.'))
         return super().form_invalid(form)


class UserDeleteView(LeaderRequiredMixin, DeleteView):
    model = User
    template_name = 'users/user_confirm_delete.html'
    success_url = reverse_lazy('users:user-list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Пользователь успешно удален'))
        return super().delete(request, *args, **kwargs)
