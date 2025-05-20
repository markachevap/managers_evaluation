from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DeleteView,
    TemplateView,
    DetailView
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.db.models import Subquery, OuterRef, Count, Avg, Q
from django.db.models.functions import Coalesce
from users.models import User
from .models import EvaluationCriteria, ManagerEvaluation, EvaluationScore
from .forms import EvaluationForm, EvaluationScoreFormSet, BulkEvaluationForm, EvaluationCriteriaForm
from django.views.generic import DetailView
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from collections import defaultdict
from decimal import Decimal, getcontext
from django.db.models import Sum
from django.core.paginator import Paginator



User = get_user_model()


getcontext().prec = 10
class ManagerStatsView(LoginRequiredMixin, DetailView):
    model = User
    template_name = 'evaluations/manager_stats.html'
    context_object_name = 'manager'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        manager = self.object

        # Получаем все оценки менеджера
        evaluations = ManagerEvaluation.objects.filter(manager=manager).order_by('-evaluation_date')
        context['evaluations'] = evaluations

        # Получаем активные критерии с весами
        criteria_list = EvaluationCriteria.objects.filter(is_active=True)
        context['criteria'] = criteria_list

        # Собираем все оценки по критериям от всех менеджеров
        from collections import defaultdict
        all_scores = defaultdict(list)

        all_evaluations = ManagerEvaluation.objects.all().prefetch_related('scores__criteria')

        for evaluation in all_evaluations:
            for score in evaluation.scores.all():
                all_scores[score.criteria_id].append(score.value)

        # Расчёт нормализованных оценок текущего менеджера
        manager_scores = defaultdict(list)
        for evaluation in evaluations:
            for score in evaluation.scores.all():
                manager_scores[score.criteria_id].append(score.value)

        criteria_stats = []
        total_score = 0  # Общая оценка менеджера

        for criteria in criteria_list:
            all_values = all_scores.get(criteria.id, [])
            if not all_values:
                continue

            total_sum = sum(all_values)
            if total_sum == 0:
                continue

            # Относительная сумма по менеджеру для этого критерия
            manager_sum = sum(manager_scores.get(criteria.id, []))
            relative_score = manager_sum / total_sum

            # Применяем вес критерия
            weighted_score = relative_score * criteria.weight
            total_score += weighted_score

            criteria_stats.append({
                'criteria': criteria,
                'avg_score': weighted_score,
                'raw_score': manager_sum,
                'relative': relative_score,
                'weight': criteria.weight,
            })

        context['criteria_stats'] = criteria_stats
        context['total_score'] = total_score

        return context

class LeaderRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.system_role == User.SYSTEM_LEADER


class ManagerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.system_role == User.SYSTEM_MANAGER


class EvaluationCriteriaListView(LeaderRequiredMixin, ListView):
    model = EvaluationCriteria
    template_name = 'evaluations/criteria_list.html'
    context_object_name = 'criterias'


class EvaluationCriteriaCreateView(CreateView):
    model = EvaluationCriteria
    form_class = EvaluationCriteriaForm
    template_name = 'evaluations/criteria_form.html'
    success_url = reverse_lazy('evaluations:criteria-list')


class EvaluationCriteriaUpdateView(UpdateView):
    model = EvaluationCriteria
    fields = ['weight']
    template_name = 'evaluations/criteria_form.html'
    success_url = reverse_lazy('evaluations:criteria-list')

    def get_queryset(self):
        return EvaluationCriteria.objects.filter(is_active=True)



class EvaluationCriteriaDeleteView(LeaderRequiredMixin, DeleteView):
    model = EvaluationCriteria
    template_name = 'evaluations/criteria_confirm_delete.html'
    success_url = reverse_lazy('evaluations:criteria-list')


class EvaluationCreateView(LeaderRequiredMixin, CreateView):
    model = ManagerEvaluation
    form_class = EvaluationForm
    template_name = 'evaluations/evaluation_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['evaluator'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = EvaluationScoreFormSet(self.request.POST)
        else:
            criteria_list = EvaluationCriteria.objects.filter(is_active=True)
            initial = [{'criteria': c} for c in criteria_list]
            context['formset'] = EvaluationScoreFormSet(queryset=EvaluationScore.objects.none(), initial=initial)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']

        self.object = form.save(commit=False)
        self.object.evaluator = self.request.user
        self.object.save()

        formset.instance = self.object

        if formset.is_valid():
            formset.save()
            return super().form_valid(form)
        else:
            return self.render_to_response(self.get_context_data(form=form))

    def get_success_url(self):
        return reverse_lazy('evaluations:evaluation-detail', kwargs={'pk': self.object.pk})



class EvaluationUpdateView(LeaderRequiredMixin, UpdateView):
    model = ManagerEvaluation
    form_class = EvaluationForm
    template_name = 'evaluations/evaluation_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = EvaluationScoreFormSet(self.request.POST, instance=self.object)
        else:
            context['formset'] = EvaluationScoreFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']

        self.object = form.save(commit=False)
        self.object.evaluator = self.request.user
        self.object.save()

        formset.instance = self.object

        if formset.is_valid():
            formset.save()
            return super().form_valid(form)
        else:
            return self.render_to_response(self.get_context_data(form=form))

    def get_success_url(self):
        return reverse_lazy('evaluations:evaluation-detail', kwargs={'pk': self.object.pk})


class EvaluationDetailView(LoginRequiredMixin, DetailView):
    model = ManagerEvaluation
    template_name = 'evaluations/evaluation_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['scores'] = self.object.scores.all().select_related('criteria')
        return context


class EvaluationListView(LeaderRequiredMixin, ListView):
    model = ManagerEvaluation
    template_name = 'evaluations/evaluation_list.html'
    context_object_name = 'evaluations'
    paginate_by = 10

    def get_queryset(self):
        return ManagerEvaluation.objects.all().order_by('-evaluation_date')


class EvaluationDeleteView(LeaderRequiredMixin, DeleteView):
    model = ManagerEvaluation
    template_name = 'evaluations/evaluation_confirm_delete.html'
    success_url = reverse_lazy('evaluations:evaluation-list')


class ManagerDashboardView(ManagerRequiredMixin, TemplateView):
    template_name = 'evaluations/manager_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Получаем все оценки текущего менеджера
        evaluations = ManagerEvaluation.objects.filter(manager=user).order_by('-evaluation_date')

        # Рассчитываем разницу между последними двумя оценками
        if evaluations.count() >= 2:
            last = evaluations[0].total_score()
            prev = evaluations[1].total_score()
            context['score_diff'] = last - prev

        # Рассчитываем позицию в рейтинге
        ranked_users = User.objects.filter(
            system_role=User.SYSTEM_MANAGER
        ).annotate(
            last_score=Coalesce(
                Subquery(
                    ManagerEvaluation.objects.filter(
                        manager=OuterRef('pk')
                    ).order_by('-evaluation_date')
                    .values('total_score')[:1]
                ),
                0.0  # Значение по умолчанию
            )
        ).order_by('-last_score')

        # Находим текущую позицию пользователя
        for rank, u in enumerate(ranked_users, start=1):
            if u.id == user.id:
                context['rank'] = rank
                break

        context['evaluations'] = evaluations
        context['user'] = user
        return context




class LeaderDashboardView(LeaderRequiredMixin, TemplateView):
    template_name = 'evaluations/leader_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Аннотируем пользователей последней оценкой
        last_evaluation = ManagerEvaluation.objects.filter(
            manager=OuterRef('pk')
        ).order_by('-evaluation_date')[:1]

        managers = User.objects.filter(
            system_role=User.SYSTEM_MANAGER
        ).annotate(
            last_score=Subquery(last_evaluation.values('total_score')),
            last_evaluation_id=Subquery(last_evaluation.values('id'))
        ).order_by('-last_score')

        # Добавляем разницу с предыдущей оценкой
        for manager in managers:
            evaluations = ManagerEvaluation.objects.filter(
                manager=manager
            ).order_by('-evaluation_date')[:2]

            if evaluations.count() >= 2:
                manager.score_diff = evaluations[0].total_score - evaluations[1].total_score
            else:
                manager.score_diff = 0

        context['managers'] = managers
        return context


class BulkEvaluationCreateView(LeaderRequiredMixin, CreateView):
    template_name = 'evaluations/bulk_evaluation_form.html'
    form_class = BulkEvaluationForm

    def form_valid(self, form):
        evaluation = ManagerEvaluation.objects.create(
            manager=form.cleaned_data['manager'],
            evaluator=self.request.user,
            evaluation_date=form.cleaned_data['evaluation_date'],
            period_start=form.cleaned_data['period_start'],
            period_end=form.cleaned_data['period_end'],
            notes=form.cleaned_data['notes']
        )

        # Сохраняем оценки по критериям
        for field, value in form.cleaned_data.items():
            if field.startswith('criteria_'):
                criterion_id = field.split('_')[1]
                EvaluationScore.objects.create(
                    evaluation=evaluation,
                    criteria_id=criterion_id,
                    value=value
                )

        return redirect('leader-dashboard')


class ComparisonView(LeaderRequiredMixin, TemplateView):
    template_name = 'evaluations/comparison.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        manager_ids = self.request.GET.getlist('managers')

        if not manager_ids:
            return context

        # Получаем выбранных менеджеров
        managers = User.objects.filter(
            id__in=manager_ids,
            system_role=User.SYSTEM_MANAGER
        )

        # Получаем все оценки выбранных менеджеров
        evaluations = ManagerEvaluation.objects.filter(
            manager__in=managers
        ).order_by('manager__last_name', '-evaluation_date')

        # Группируем оценки по менеджерам
        manager_data = []
        for manager in managers:
            manager_evals = evaluations.filter(manager=manager)
            if manager_evals.exists():
                manager_data.append({
                    'manager': manager,
                    'evaluations': manager_evals,
                    'last_score': manager_evals.first().total_score(),
                })

        # Сортируем по последней оценке
        manager_data.sort(key=lambda x: x['last_score'], reverse=True)

        context['manager_data'] = manager_data
        context['criterias'] = EvaluationCriteria.objects.filter(is_active=True)
        return context