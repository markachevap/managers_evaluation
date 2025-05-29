from django.test import TestCase
from users.models import User

class UserModelTest(TestCase):

    def setUp(self):
        User.objects.create(first_name = 'Кирилл', last_name = 'Black', 
                username = 'kirblack', email = 'kirill@mail.ru')

    def tearDown(self):
        # Очистка после каждого метода
        pass

    def test_email_label(self):
        user = User.objects.get(id = 1)
        email_label = user._meta.get_field("email").verbose_name
        self.assertEqual(email_label, 'адрес электронной почты')

    def test_email_exists(self):
        is_exists = False
        try:
            User.objects.create(first_name = 'Кирилл', last_name = 'Black', 
                    username = 'kirblack', email = 'kirill@mail.ru')
        except:
            is_exists = True

        self.assertTrue(is_exists)

        