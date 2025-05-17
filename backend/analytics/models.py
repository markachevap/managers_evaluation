from django.db import models
from django.utils.translation import gettext_lazy as _
from users.models import User

class ReportTemplate(models.Model):
    name = models.CharField(_('Название'), max_length=100)
    description = models.TextField(_('Описание'), blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('Создатель')
    )
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    is_default = models.BooleanField(_('По умолчанию'), default=False)

    def __str__(self):
        return self.name

class SavedReport(models.Model):
    name = models.CharField(_('Название'), max_length=100)
    report_data = models.JSONField(_('Данные отчета'))
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('Создатель')
    )
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    evaluation = models.ForeignKey(
        'evaluations.ManagerEvaluation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='saved_reports',
        verbose_name=_('Связанная оценка')
    )

    def __str__(self):
        return f"{self.name} (от {self.created_by})"


class ComparisonReport(models.Model):
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('Создатель')
    )
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    managers = models.ManyToManyField(
        User,
        related_name='comparison_reports',
        limit_choices_to={'system_role': User.SYSTEM_MANAGER}
    )
    report_data = models.JSONField(_('Данные сравнения'))

    def save(self, *args, **kwargs):
        # Автоматическое вычисление разниц и рейтинга
        if not self.report_data:
            self.report_data = self.calculate_comparison()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('comparison-report-detail', kwargs={'pk': self.pk})

    def get_managers_list(self):
        return ", ".join([m.get_full_name() for m in self.managers.all()])

    get_managers_list.short_description = _('Менеджеры')

    def calculate_comparison(self):
        """
        Вычисляет сравнение менеджеров по их оценкам, включая:
        - Графики по каждому критерию
        - Разницу между последней и предпоследней оценкой
        - Общий рейтинг
        Возвращает данные в формате, готовом для отображения в интерфейсе
        """
        comparison_data = {
            'managers': [],
            'criteria_charts': {},
            'overall_chart': {
                'labels': [],
                'datasets': []
            },
            'rating': []
        }

        # Получаем всех менеджеров для сравнения
        managers = self.managers.all().prefetch_related(
            'evaluations__scores__criteria'
        ).order_by('-evaluations__total_score')

        # Собираем все даты оценок для оси X графиков
        all_dates = sorted(list(set(
            eval.evaluation_date
            for manager in managers
            for eval in manager.evaluations.all()
        )))

        comparison_data['overall_chart']['labels'] = [
            date.strftime('%Y-%m-%d') for date in all_dates
        ]

        # Для каждого критерия готовим структуру для графика
        criteria = EvaluationCriteria.objects.filter(is_active=True)
        for criterion in criteria:
            comparison_data['criteria_charts'][criterion.name] = {
                'labels': [date.strftime('%Y-%m-%d') for date in all_dates],
                'datasets': []
            }

        # Обрабатываем каждого менеджера
        for i, manager in enumerate(managers):
            manager_data = {
                'id': manager.id,
                'name': manager.get_full_name(),
                'position': manager.position,
                'status': manager.get_company_status_display(),
                'evaluations': [],
                'difference': None,
                'rating_position': i + 1
            }

            evaluations = manager.evaluations.order_by('evaluation_date')
            last_two = list(evaluations[:2])

            # Вычисляем разницу между последними двумя оценками
            if len(last_two) == 2:
                difference = last_two[0].total_score - last_two[1].total_score
                manager_data['difference'] = {
                    'value': abs(difference),
                    'sign': '+' if difference >= 0 else '-',
                    'color': 'green' if difference >= 0 else 'red'
                }

            # Формируем данные для общего графика
            dataset = {
                'label': manager.get_full_name(),
                'data': [],
                'borderColor': f'hsl({i * 360 / len(managers)}, 70%, 50%)',
                'backgroundColor': f'hsl({i * 360 / len(managers)}, 70%, 50%)'
            }

            # Заполняем данные для каждой даты
            for date in all_dates:
                eval = evaluations.filter(evaluation_date=date).first()
                if eval:
                    dataset['data'].append(float(eval.total_score))
                else:
                    dataset['data'].append(None)

            comparison_data['overall_chart']['datasets'].append(dataset)

            # Формируем данные для графиков по критериям
            for criterion in criteria:
                criterion_dataset = {
                    'label': manager.get_full_name(),
                    'data': [],
                    'borderColor': f'hsl({i * 360 / len(managers)}, 70%, 50%)',
                    'backgroundColor': f'hsl({i * 360 / len(managers)}, 70%, 50%)'
                }

                for date in all_dates:
                    eval = evaluations.filter(evaluation_date=date).first()
                    if eval:
                        score = eval.scores.filter(criteria=criterion).first()
                        criterion_dataset['data'].append(
                            float(score.value) if score else None
                        )
                    else:
                        criterion_dataset['data'].append(None)

                comparison_data['criteria_charts'][criterion.name]['datasets'].append(criterion_dataset)

            comparison_data['managers'].append(manager_data)
            comparison_data['rating'].append({
                'id': manager.id,
                'name': manager.get_full_name(),
                'position': manager.position,
                'score': evaluations.first().total_score if evaluations.exists() else 0
            })

        # Сортируем рейтинг по убыванию оценки
        comparison_data['rating'].sort(key=lambda x: x['score'], reverse=True)

        return comparison_data