from django.contrib.auth.models import AbstractUser, Group, Permission
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class CustomRole(models.Model):
    """
    Модель для кастомных ролей, создаваемых руководителями
    """
    name = models.CharField(_('Название роли'), max_length=100, unique=True)
    description = models.TextField(_('Описание'), blank=True)
    created_by = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='created_roles',
        verbose_name=_('Создатель')
    )
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    is_active = models.BooleanField(_('Активна'), default=True)

    # Связь с Django Group для разрешений
    group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_('Группа разрешений')
    )

    class Meta:
        verbose_name = _('Кастомная роль')
        verbose_name_plural = _('Кастомные роли')
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['created_by', 'name'],
                name='unique_role_name_per_creator'
            )
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.name:
            raise ValueError("Название роли не может быть пустым")

        # Очистка имени для группы (удаляем спецсимволы)
        group_name = f"Role_{self.name.strip()}"[:150]  # Ограничиваем длину
        group_name = ''.join(c for c in group_name if c.isalnum() or c in ['_', ' '])

        if not self.group:
            group, created = Group.objects.get_or_create(name=group_name)
            self.group = group
        else:
            # Обновляем имя группы, если изменилось имя роли
            if self.group.name != group_name:
                self.group.name = group_name
                self.group.save()

        super().save(*args, **kwargs)


class User(AbstractUser):
    email = models.EmailField(
        _('email address'),
        unique=True,
        error_messages={
            'unique': _("A user with that email already exists."),
        }
    )
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'username']

    # Системные роли
    SYSTEM_LEADER = 'system_leader'
    SYSTEM_MANAGER = 'system_manager'

    SYSTEM_ROLE_CHOICES = [
        (SYSTEM_LEADER, _('Руководитель')),
        (SYSTEM_MANAGER, _('Менеджер')),
    ]

    system_role = models.CharField(
        _('Системная роль'),
        max_length=20,
        choices=SYSTEM_ROLE_CHOICES,
        default=SYSTEM_MANAGER
    )
    custom_role = models.ForeignKey(
        CustomRole,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name=_('Кастомная роль')
    )
    hire_date = models.DateField(
        _('Дата приема на работу'),
        null=True,
        blank=True
    )
    position = models.CharField(
        _('Должность'),
        max_length=100,
        blank=True
    )

    class Meta:
        verbose_name = _('Пользователь')
        verbose_name_plural = _('Пользователи')
        ordering = ['last_name', 'first_name']

    @property
    def role(self):
        """Возвращает строковое представление роли"""
        if self.custom_role:
            return str(self.custom_role)
        return self.get_system_role_display()

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        # При создании руководителя сбрасываем кастомную роль
        if self.system_role == User.SYSTEM_LEADER:
            self.custom_role = None

        # Нормализуем email
        self.email = self.__class__.objects.normalize_email(self.email)
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()

        if self.hire_date and self.hire_date > timezone.now().date():
            raise ValidationError({'hire_date': _('Дата приема не может быть в будущем')})

        if self.system_role == User.SYSTEM_LEADER and self.custom_role:
            raise ValidationError(
                {'custom_role': _('Руководители не могут иметь кастомные роли')}
            )

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})" if self.get_full_name() else self.email