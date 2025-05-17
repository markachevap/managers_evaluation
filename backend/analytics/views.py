from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from users.models import User
from evaluations.models import ManagerEvaluation, EvaluationCriteria,  EvaluationScore
from django.db.models import Subquery, OuterRef, Avg, FloatField, Q
from django.db.models.functions import Coalesce



class LeaderAnalyticsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'analytics/leader_analytics.html'

    def test_func(self):
        return self.request.user.system_role == User.SYSTEM_LEADER

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Получаем последние оценки для каждого менеджера
        last_evaluations = ManagerEvaluation.objects.filter(
            pk__in=Subquery(
                ManagerEvaluation.objects.order_by('manager', '-evaluation_date')
                .distinct('manager')
                .values('pk')
            )
        )

        # Аннотируем пользователей последней оценкой
        managers = User.objects.filter(
            system_role=User.SYSTEM_MANAGER
        ).annotate(
            last_score=Subquery(
                last_evaluations.filter(
                    manager=OuterRef('pk')
                ).annotate(
                    calculated_score=Coalesce(
                        Avg('scores__value') * Avg('scores__criteria__weight'),
                        0.0,
                        output_field=FloatField()
                    )
                ).values('calculated_score')[:1]
            )
        ).order_by('-last_score')

        # Добавляем разницу с предыдущей оценкой
        for manager in managers:
            evaluations = ManagerEvaluation.objects.filter(
                manager=manager
            ).annotate(
                calculated_score=Coalesce(
                    Avg('scores__value') * Avg('scores__criteria__weight'),
                    0.0,
                    output_field=FloatField()
                )
            ).order_by('-evaluation_date')[:2]

            if evaluations.count() >= 2:
                manager.score_diff = evaluations[0].calculated_score - evaluations[1].calculated_score
            else:
                manager.score_diff = 0

        context['managers'] = managers[:5]  # Только топ-5

        # Средние оценки по критериям
        criteria_stats = []
        active_criteria = EvaluationCriteria.objects.filter(is_active=True)

        for criteria in active_criteria:
            avg_score = EvaluationScore.objects.filter(
                criteria=criteria
            ).aggregate(avg=Avg('value'))['avg'] or 0

            criteria_stats.append({
                'criteria': criteria,
                'avg_score': avg_score
            })

        context['criteria_stats'] = criteria_stats

        evaluations = ManagerEvaluation.objects.filter(
            manager__in=managers
        ).order_by('evaluation_date')

        context['chart_data'] = {
            'labels': [e.evaluation_date.strftime('%Y-%m-%d') for e in evaluations],
            'datasets': [
                {
                    'label': criteria.get_criteria_type_display(),
                    'data': [
                        score.value
                        for score in EvaluationScore.objects.filter(
                            criteria=criteria,
                            evaluation__in=evaluations
                        )
                    ],
                    'borderColor': '#4CAF50',
                }
                for criteria in EvaluationCriteria.objects.filter(is_active=True)
            ]
        }
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


class ManagerAnalyticsView(LoginRequiredMixin, UserPassesTestMixin, BaseAnalyticsMixin, TemplateView):
    """Персональная аналитика для менеджеров"""


    template_name = 'analytics/manager_analytics.html'

    def test_func(self):
        return self.request.user.system_role == User.SYSTEM_MANAGER

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        period = self.get_current_period()

        evaluations = ManagerEvaluation.objects.filter(
            manager=user,
            evaluation_date__range=[period['start'], period['end']]
        ).order_by('evaluation_date')

        criteria_data = []
        for criteria in EvaluationCriteria.objects.filter(is_active=True):
            scores = evaluations.annotate(
                criteria_score=Subquery(
                    EvaluationScore.objects.filter(
                        evaluation=OuterRef('pk'),
                        criteria=criteria
                    ).values('value')[:1]
                )
            ).values_list('evaluation_date', 'criteria_score')

            criteria_data.append({
                'criteria': criteria,
                'scores': list(scores),
                'avg_score': evaluations.aggregate(
                    avg=Avg('scores__value', filter=Q(scores__criteria=criteria))
                )['avg'] or 0
            })

        context.update({
            'evaluations': evaluations,
            'criteria_data': criteria_data,
            'current_score': evaluations.last().total_score() if evaluations.exists() else None,
            'improvement_suggestions': self.get_improvement_suggestions(user),
        })

        context['current_score'] = evaluations.last().total_score() if evaluations.exists() else 0

        context['chart_data'] = {
            'labels': [e.evaluation_date.strftime('%Y-%m-%d') for e in evaluations],
            'datasets': [
                {
                    'label': criteria.get_criteria_type_display(),
                    'data': [
                        score.value
                        for score in EvaluationScore.objects.filter(
                            criteria=criteria,
                            evaluation__in=evaluations
                        )
                    ],
                    'borderColor': '#4CAF50',
                }
                for criteria in EvaluationCriteria.objects.filter(is_active=True)
            ]
        }

        return context

    def get_improvement_suggestions(self, user):
        """Генерация рекомендаций по улучшению"""
        from collections import defaultdict
        suggestions = defaultdict(list)

        last_eval = ManagerEvaluation.objects.filter(
            manager=user
        ).order_by('-evaluation_date').first()

        if last_eval:
            for score in last_eval.scores.all():
                if score.value < 7:  # Пример порога для рекомендаций
                    suggestions['criteria'].append(score.criteria.name)
                    suggestions['suggestions'].append(
                        f"Улучшите показатели по критерию '{score.criteria.name}'. "
                        f"Текущая оценка: {score.value}"
                    )

        return suggestions


class ComparisonAnalyticsView(LoginRequiredMixin, UserPassesTestMixin, BaseAnalyticsMixin, TemplateView):
    """Углубленное сравнение менеджеров"""
    template_name = 'analytics/comparison_analytics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        manager_ids = self.request.GET.getlist('managers')

        if not manager_ids:
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

        context['managers'] = managers

        context['chart_data'] = {
            'labels': [e.evaluation_date.strftime('%Y-%m-%d') for e in evaluations],
            'datasets': [
                {
                    'label': f"{manager.get_full_name()} ({criteria.name})",
                    'data': [
                        score.value
                        for score in EvaluationScore.objects.filter(
                            criteria=criteria,
                            evaluation__manager=manager
                        )
                    ],
                    'borderColor': f"#{hash(manager.id + criteria.id) % 0xFFFFFF:06x}",  # Разные цвета
                }
                for manager in managers
                for criteria in EvaluationCriteria.objects.filter(is_active=True)
            ]
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