from django.db import models
from django.utils.translation import gettext_lazy as _
from users.models import User
from django.core.exceptions import ValidationError

class EvaluationCriteria(models.Model):
    PRODUCTION = 'production'
    CLIENT_SATISFACTION = 'clients'
    PLANS = 'plans'
    TEAMWORK = 'teamwork'
    DEVELOPMENT = 'development'

    CRITERIA_TYPES = [
        (PRODUCTION, _('Производственные показатели')),
        (CLIENT_SATISFACTION, _('Удовлетворенность клиентов')),
        (PLANS, _('Выполнение плановых показателей')),
        (TEAMWORK, _('Командная работа')),
        (DEVELOPMENT, _('Личные достижения и развитие')),
    ]

    criteria_type = models.CharField(
        _('Тип критерия'),
        max_length=100,
        choices=CRITERIA_TYPES,
        default='production',
        unique=True
    )
    weight = models.FloatField(default=0.0)  # Поле для веса
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(weight__gte=0) & models.Q(weight__lte=1),
                name='weight_range'
            )
        ]

    def clean(self):
        if self.weight < 0 or self.weight > 1:
            raise ValidationError("Вес должен быть от 0 до 1")
        total_weight = \
        EvaluationCriteria.objects.filter(is_active=True).exclude(id=self.id).aggregate(models.Sum('weight'))[
            'weight__sum'] or 0
        if total_weight + self.weight > 1:
            raise ValidationError("Сумма весов всех критериев не должна превышать 1")

    def __str__(self):
        return f"{self.get_criteria_type_display()}"


class ManagerEvaluation(models.Model):
    """
    Оценка менеджера за определенный период
    """
    manager = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='evaluations',
        verbose_name=_('Менеджер'),
        limit_choices_to={'system_role': User.SYSTEM_MANAGER}  # Ограничение только для менеджеров
    )
    evaluator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_evaluations',
        verbose_name=_('Оценщик'),
        limit_choices_to={'system_role': User.SYSTEM_LEADER}
    )
    evaluation_date = models.DateField(_('Дата оценки'))
    period_start = models.DateField(_('Начало периода'))
    period_end = models.DateField(_('Конец периода'))
    notes = models.TextField(_('Комментарии'), blank=True)

    total_score = models.FloatField(
        _('Общий балл'),
        editable=False,
        null=True,
        blank=True,
        help_text=_('Автоматически рассчитывается из оценок по критериям')
    )

    class Meta:
        verbose_name = _('Оценка менеджера')
        verbose_name_plural = _('Оценки менеджеров')
        ordering = ['-evaluation_date']
        unique_together = ['manager', 'period_start', 'period_end']

    def calculate_total_score(self):
        if not self.pk:
            # Если объект ещё не сохранён — возвращаем None
            return None
        scores = self.scores.select_related('criteria').all()
        if scores.exists():
            return sum(score.value * score.criteria.weight for score in scores if score.criteria.is_active)
        return None

    def clean(self):
        if self.period_start is None or self.period_end is None:
            raise ValidationError("Дата начала и дата окончания должны быть указаны.")

        if self.period_start >= self.period_end:
            raise ValidationError("Дата начала не может быть позже даты окончания")

    def save(self, *args, **kwargs):
        self.total_score = self.calculate_total_score()
        super().save(*args, **kwargs)


class EvaluationScore(models.Model):
    """
    Оценка по конкретному критерию
    """
    evaluation = models.ForeignKey(
        ManagerEvaluation,
        on_delete=models.CASCADE,
        related_name='scores',
        verbose_name=_('Оценка менеджера')
    )
    criteria = models.ForeignKey(
        EvaluationCriteria,
        on_delete=models.CASCADE,
        verbose_name=_('Критерий оценки')
    )
    value = models.FloatField(
        _('Значение'),
        help_text=_('Оценка по данному критерию')
    )
    comment = models.TextField(_('Комментарий'), blank=True)

    class Meta:
        verbose_name = _('Оценка по критерию')
        verbose_name_plural = _('Оценки по критериям')
        unique_together = ('evaluation', 'criteria')
        ordering = ['criteria_id']

    def __str__(self):
        return f"{self.criteria}: {self.value}"

    def weighted_score(self):
        """Возвращает взвешенную оценку"""
        return round(self.value * self.criteria.weight, 2)

    weighted_score.short_description = _('Взвешенная оценка')

