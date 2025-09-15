from django.test import TestCase
from evaluations.models import EvaluationCriteria, EvaluationScore


class EvaluationModelTest(TestCase):

    def setUp(self):
        EvaluationCriteria.objects.create(criteria_type = EvaluationCriteria.PRODUCTION, weight = 0.5)
        EvaluationCriteria.objects.create(criteria_type = EvaluationCriteria.PLANS, weight = 0.5)
        # EvaluationScore.objects.create(criteria = EvaluationCriteria.objects.get(id = 1), value = 8)
        # EvaluationScore.objects.create(criteria = EvaluationCriteria.objects.get(id = 2), value = 6)
        
    def tearDown(self):
        # Очистка после каждого метода
        pass

    def test_label(self):
        self.assertTrue(True)

    

# Create your tests here.
