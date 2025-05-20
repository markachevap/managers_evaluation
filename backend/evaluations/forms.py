from django import forms
from .models import ManagerEvaluation, EvaluationScore, EvaluationCriteria
from django.forms import inlineformset_factory
from django.contrib.auth import get_user_model


User = get_user_model()

class BulkEvaluationForm(forms.Form):
    def clean(self):
        cleaned_data = super().clean()
        for field in self.fields:
            if field.startswith('criteria_') and cleaned_data.get(field):
                if not (0 <= cleaned_data[field] <= 100):
                    self.add_error(field, "Оценка должна быть от 0 до 100")
        return cleaned_data


class EvaluationForm(forms.ModelForm):
    class Meta:
        model = ManagerEvaluation
        fields = ['manager', 'evaluation_date', 'period_start', 'period_end', 'notes']

    def __init__(self, *args, evaluator=None, **kwargs):
        super().__init__(*args, **kwargs)
        if evaluator:
            self.evaluator = evaluator


class EvaluationScoreForm(forms.ModelForm):
    value = forms.FloatField(
        label='Оценка',
        min_value=0,
        max_value=10,
        widget=forms.NumberInput(attrs={
            'step': 0.1,
            'class': 'form-control'
        })
    )

    class Meta:
        model = EvaluationScore
        fields = ['criteria', 'value', 'comment']


class EvaluationCriteriaForm(forms.ModelForm):
    class Meta:
        model = EvaluationCriteria
        fields = ['criteria_type', 'weight', 'description', 'is_active']


# Formset для оценок по критериям
EvaluationScoreFormSet = inlineformset_factory(
    ManagerEvaluation,
    EvaluationScore,
    form=EvaluationScoreForm,
    fields=('criteria', 'value', 'comment'),
    extra=0,
    can_delete=False
)
