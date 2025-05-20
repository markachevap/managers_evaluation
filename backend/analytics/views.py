from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from users.models import User
from evaluations.models import ManagerEvaluation, EvaluationCriteria,  EvaluationScore
from django.db.models import Subquery, OuterRef, Avg, FloatField, Q, Sum, F
from django.db.models.functions import Coalesce
from django.db import models
from django.shortcuts import get_object_or_404
from datetime import date, timedelta
from django.http import HttpResponse


class LeaderAnalyticsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'analytics/leader_analytics.html'

    def test_func(self):
        return self.request.user.system_role == User.SYSTEM_LEADER

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Получаем все активные критерии оценки
        active_criteria = EvaluationCriteria.objects.filter(is_active=True)

        # Получаем последних оценки для каждого менеджера
        last_evaluations = ManagerEvaluation.objects.values('manager').annotate(
            last_evaluation_date=models.Max('evaluation_date')
        ).values('manager', 'last_evaluation_date')

        # Получаем ID последних оценок
        last_evaluation_ids = []
        for eval in last_evaluations:
            last_evaluation_ids.append(
                ManagerEvaluation.objects.filter(
                    manager=eval['manager'],
                    evaluation_date=eval['last_evaluation_date']
                ).values_list('id', flat=True).first()
            )

        # Фильтруем оценки по ID
        last_evaluations = ManagerEvaluation.objects.filter(id__in=last_evaluation_ids)

        # Получаем всех менеджеров с системной ролью SYSTEM_MANAGER
        managers = User.objects.filter(system_role=User.SYSTEM_MANAGER)

        # Аннотируем менеджеров последней оценкой, используя Subquery и Coalesce
        managers = managers.annotate(
            last_score=Coalesce(
                Subquery(
                    last_evaluations.filter(manager=OuterRef('pk')).annotate(
                        calculated_score=Sum(
                            F('scores__value') * F('scores__criteria__weight'),
                            output_field=FloatField()
                        )
                    ).values('calculated_score')[:1]
                ),
                0.0,
                output_field=FloatField()
            )
        )

        # Получаем лучшего менеджера
        top_manager = managers.order_by('-last_score').first()

        # Добавляем разницу с предыдущей оценкой для топ-5 менеджеров
        top_managers = managers.order_by('-last_score')[:5]
        for manager in top_managers:
            evaluations = ManagerEvaluation.objects.filter(manager=manager).order_by('-evaluation_date')[:2]
            if len(evaluations) >= 2:
                manager.score_diff = evaluations[0].total_score - evaluations[1].total_score
            else:
                manager.score_diff = 0

        context['managers'] = managers
        context['top_manager'] = top_manager
        context['total_managers'] = User.objects.filter(system_role=User.SYSTEM_MANAGER).count()
        context['evaluations_count'] = ManagerEvaluation.objects.count()

        # Средние оценки по критериям
        criteria_stats = []
        for criteria in active_criteria:
            avg_score = EvaluationScore.objects.filter(criteria=criteria).aggregate(avg=Avg('value'))['avg'] or 0
            criteria_stats.append({
                'criteria': criteria,
                'avg_score': avg_score
            })

        context['criteria_stats'] = criteria_stats

        # Подготовка данных для графика динамики оценок
        # (Этот код может потребовать дополнительной оптимизации)
        all_evaluations = ManagerEvaluation.objects.filter(manager__in=top_managers).order_by('evaluation_date')
        chart_data = {
            'labels': [e.evaluation_date.strftime('%Y-%m-%d') for e in all_evaluations],
            'datasets': []
        }

        for criteria in active_criteria:
            dataset = {
                'label': criteria.get_criteria_type_display(),
                'data': [
                    float(EvaluationScore.objects.filter(criteria=criteria, evaluation=e).aggregate(Avg('value'))['avg'] or 0)
                    for e in all_evaluations
                ],
                'borderColor': '#4CAF50',
            }
            chart_data['datasets'].append(dataset)

        context['chart_data'] = chart_data
        # Вычисление средней оценки всех менеджеров
        context['avg_score'] = ManagerEvaluation.objects.all().aggregate(avg=Avg('total_score'))['avg'] or 0
        criteria_stats_with_hsl = []
        for i, stat in enumerate(criteria_stats):
            hsl_value = (i * 30) % 360  # Ensures value stays within 0-359
            criteria_stats_with_hsl.append({
                'criteria': stat['criteria'],
                'avg_score': stat['avg_score'],
                'hsl': hsl_value,
            })
        context['criteria_stats_with_hsl'] = criteria_stats_with_hsl
        return context


class BaseAnalyticsMixin:
    """Общая логика для аналитики"""

    def get_common_context(self):
        # Основные критерии для аналитики
        criterias = EvaluationCriteria.objects.filter(is_active=True)
        return {
            'criterias': criterias,
            'current_period': self.get_current_period(),
        }

    def get_current_period(self):
        # Логика определения текущего отчетного периода
        from datetime import date
        today = date.today()
        return {
            'start': date(today.year, today.month, 1),
            'end': today
        }


class ManagerAnalyticsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'analytics/manager_analytics.html'

    def test_func(self):
        # Проверка, является ли пользователь SYSTEM_LEADER или пытается просмотреть свой собственный профиль
        manager_id = self.kwargs.get('manager_id')
        return self.request.user.system_role == User.SYSTEM_LEADER or self.request.user.id == int(manager_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        manager_id = self.kwargs.get('manager_id')
        manager = get_object_or_404(User, pk=manager_id, system_role=User.SYSTEM_MANAGER)
        evaluations = ManagerEvaluation.objects.filter(manager=manager).order_by('evaluation_date')

        # Подготовка данных для графика
        chart_data = {
            'labels': [e.evaluation_date.strftime('%Y-%m-%d') for e in evaluations],
            'datasets': [{
                'label': 'Общая оценка',
                'data': [e.total_score for e in evaluations],
                'borderColor': '#4CAF50', # Зеленый цвет
            }]
        }
        context['chart_data'] = chart_data
        # Получение текущей оценки
        current_score = evaluations.last().total_score if evaluations.exists() else None
        context['current_score'] = current_score

        # Расчет разницы (Delta)
        delta = None
        if evaluations.count() >= 2:
            delta = evaluations.last().total_score - evaluations[evaluations.count() - 2].total_score # Получаем предпоследнюю оценку
        context['delta'] = delta

        # Получение позиции в рейтинге
        all_managers = User.objects.filter(system_role=User.SYSTEM_MANAGER)
        manager_scores = {}
        for manager in all_managers:
          last_evaluation = ManagerEvaluation.objects.filter(manager=manager).order_by('-evaluation_date').first()
          if last_evaluation:
              manager_scores[manager.id] = last_evaluation.total_score
          else:
            manager_scores[manager.id] = 0 # Если нет оценок - 0

        sorted_scores = sorted(manager_scores.items(), key=lambda item: item[1], reverse=True)
        rank_position = 0
        for i, (manager_id, score) in enumerate(sorted_scores):
          if manager_id == int(manager_id):
            rank_position = i + 1
            break
        context['rank_position'] = rank_position
        context['total_managers'] = all_managers.count()

        # Получение рекомендаций (пример)
        improvement_suggestions = self.get_improvement_suggestions(manager)
        context['improvement_suggestions'] = improvement_suggestions
        context['manager'] = manager
        return context

    def get_improvement_suggestions(self, manager):
        """Пример получения рекомендаций по улучшению"""
        # Здесь должна быть ваша логика для генерации рекомендаций на основе данных
        suggestions = []
        # Получаем все критерии
        criteria = EvaluationCriteria.objects.all()
        for criterion in criteria:
          last_score = EvaluationScore.objects.filter(criteria=criterion, evaluation__manager=manager).order_by('-evaluation__evaluation_date').first()
          if last_score and last_score.value < 5:
            suggestions.append(f"Уделите больше внимания критерию '{criterion.name}'.")
        return {'suggestions': suggestions}


class ComparisonAnalyticsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Углубленное сравнение менеджеров"""
    template_name = 'analytics/comparison_analytics.html'

    def test_func(self):
        return self.request.user.system_role == User.SYSTEM_LEADER  
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        manager_ids = self.request.GET.getlist('managers')

        if not manager_ids:
            context['all_managers'] = User.objects.filter(system_role=User.SYSTEM_MANAGER)
            return context

        managers = User.objects.filter(
            id__in=manager_ids,
            system_role=User.SYSTEM_MANAGER
        ).prefetch_related('evaluations__scores')

        comparison_data = []
        for manager in managers:
            evaluations = manager.evaluations.order_by('-evaluation_date')
            if not evaluations.exists():
                continue

            last_eval = evaluations.first()
            criteria_scores = {
                score.criteria.name: score.value
                for score in last_eval.scores.all()
            }

            comparison_data.append({
                'manager': manager,
                'total_score': last_eval.total_score(),
                'criteria_scores': criteria_scores,
                'progress': self.calculate_progress(manager),
            })

        context['comparison_data'] = sorted(
            comparison_data,
            key=lambda x: x['total_score'],
            reverse=True
        )
        # Расчет рейтинга и процента для радиального графика
        max_score = max([data['total_score'] for data in comparison_data], default=0)
        for i, data in enumerate(context['comparison_data']):
            data['rating_position'] = i + 1
            data['total_score_percent'] = (data['total_score'] / max_score) * 100 if max_score > 0 else 0

        context['managers'] = managers
        context['all_managers'] = User.objects.filter(system_role=User.SYSTEM_MANAGER)
        context['selected_manager_ids'] = manager_ids

        # Подготовка данных для графика
        trend_labels = []
        trend_datasets = []

        # Line Chart
        for manager in managers:
            trend_dataset_data = []
            evaluations = ManagerEvaluation.objects.filter(manager=manager).order_by('evaluation_date')
            trend_labels = [e.evaluation_date.strftime('%Y-%m-%d') for e in evaluations]
            trend_datasets.append({
                'label': manager.get_full_name(),
                'data': [e.total_score for e in evaluations],
                'borderColor': f"#{hash(manager.id) % 0xFFFFFF:06x}",  # Разные цвета
            })

        context['chart_data'] = {
            'trend_labels': trend_labels,
            'trend_datasets': trend_datasets,
        }

        return context

    def calculate_progress(self, manager):
        """Расчет прогресса за последние 3 периода"""
        evaluations = manager.evaluations.order_by('-evaluation_date')[:3]
        if len(evaluations) < 2:
            return 0

        current = evaluations[0].total_score()
        previous = evaluations[1].total_score()
        return round(current - previous, 2)
