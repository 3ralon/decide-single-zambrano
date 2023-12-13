import random
import itertools
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import Client, RequestFactory, TestCase

from selenium import webdriver
from selenium.webdriver.common.by import By

from base import mods
from base.tests import BaseTestCase
from census.models import Census
from mixnet.mixcrypt import ElGamal
from mixnet.mixcrypt import MixCrypt
from mixnet.models import Auth
from voting.models import Voting, Question, QuestionOption
from voting.forms import QuestionForm, QuestionOptionFormSet


class VotingTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def encrypt_msg(self, msg, v, bits=settings.KEYBITS):
        pk = v.pub_key
        p, g, y = (pk.p, pk.g, pk.y)
        k = MixCrypt(bits=bits)
        k.k = ElGamal.construct((p, g, y))
        return k.encrypt(msg)

    def create_voting(self):
        q = Question(desc="test question")
        q.save()
        for i in range(5):
            opt = QuestionOption(question=q, option="option {}".format(i + 1))
            opt.save()
        v = Voting(name="test voting", question=q)
        v.save()

        a, _ = Auth.objects.get_or_create(
            url=settings.BASEURL, defaults={"me": True, "name": "test auth"}
        )
        a.save()
        v.auths.add(a)

        return v

    def create_voters(self, v):
        for i in range(100):
            u, _ = User.objects.get_or_create(username="testvoter{}".format(i))
            u.is_active = True
            u.save()
            c = Census(voter_id=u.id, voting_id=v.id)
            c.save()

    def get_or_create_user(self, pk):
        user, _ = User.objects.get_or_create(pk=pk)
        user.username = "user{}".format(pk)
        user.set_password("qwerty")
        user.save()
        return user

    def store_votes(self, v):
        voters = list(Census.objects.filter(voting_id=v.id))
        voter = voters.pop()

        clear = {}
        for opt in v.question.options.all():
            clear[opt.number] = 0
            for i in range(random.randint(0, 5)):
                a, b = self.encrypt_msg(opt.number, v)
                data = {
                    "voting": v.id,
                    "voter": voter.voter_id,
                    "vote": {"a": a, "b": b},
                }
                clear[opt.number] += 1
                user = self.get_or_create_user(voter.voter_id)
                self.login(user=user.username)
                voter = voters.pop()
                mods.post("store", json=data)
        return clear

    """def test_complete_voting(self):
        v = self.create_voting()
        self.create_voters(v)

        v.create_pubkey()
        v.start_date = timezone.now()
        v.save()

        clear = self.store_votes(v)

        self.login()  # set token
        v.tally_votes(self.token)

        tally = v.tally
        tally.sort()
        tally = {k: len(list(x)) for k, x in itertools.groupby(tally)}

        for q in v.question.options.all():
            self.assertEqual(tally.get(q.number, 0), clear.get(q.number, 0))

        for q in v.postproc:
            self.assertEqual(tally.get(q["number"], 0), q["votes"])"""

    def test_create_voting_from_api(self):
        data = {"name": "Example"}
        response = self.client.post("/voting/", data, format="json")
        self.assertEqual(response.status_code, 401)

        # login with user no admin
        self.login(user="noadmin")
        response = mods.post("voting", params=data, response=True)
        self.assertEqual(response.status_code, 403)

        # login with user admin
        self.login()
        response = mods.post("voting", params=data, response=True)
        self.assertEqual(response.status_code, 400)

        data = {
            "name": "Example",
            "desc": "Description example",
            "question": "I want a ",
            "question_type": "DEFAULT",
            "question_opt": ["cat", "dog", "horse"],
        }

        response = self.client.post("/voting/", data, format="json")
        self.assertEqual(response.status_code, 201)

    def test_update_voting(self):
        voting = self.create_voting()

        data = {"action": "start"}
        # response = self.client.post('/voting/{}/'.format(voting.pk), data, format='json')
        # self.assertEqual(response.status_code, 401)

        # login with user no admin
        self.login(user="noadmin")
        response = self.client.put("/voting/{}/".format(voting.pk), data, format="json")
        self.assertEqual(response.status_code, 403)

        # login with user admin
        self.login()
        data = {"action": "bad"}
        response = self.client.put("/voting/{}/".format(voting.pk), data, format="json")
        self.assertEqual(response.status_code, 400)

        # STATUS VOTING: not started
        for action in ["stop", "tally"]:
            data = {"action": action}
            response = self.client.put(
                "/voting/{}/".format(voting.pk), data, format="json"
            )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json(), "Voting is not started")

        data = {"action": "start"}
        response = self.client.put("/voting/{}/".format(voting.pk), data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), "Voting started")

        # STATUS VOTING: started
        data = {"action": "start"}
        response = self.client.put("/voting/{}/".format(voting.pk), data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), "Voting already started")

        data = {"action": "tally"}
        response = self.client.put("/voting/{}/".format(voting.pk), data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), "Voting is not stopped")

        data = {"action": "stop"}
        response = self.client.put("/voting/{}/".format(voting.pk), data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), "Voting stopped")

        # STATUS VOTING: stopped
        data = {"action": "start"}
        response = self.client.put("/voting/{}/".format(voting.pk), data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), "Voting already started")

        data = {"action": "stop"}
        response = self.client.put("/voting/{}/".format(voting.pk), data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), "Voting already stopped")

        data = {"action": "tally"}
        response = self.client.put("/voting/{}/".format(voting.pk), data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), "Voting tallied")

        # STATUS VOTING: tallied
        data = {"action": "start"}
        response = self.client.put("/voting/{}/".format(voting.pk), data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), "Voting already started")

        data = {"action": "stop"}
        response = self.client.put("/voting/{}/".format(voting.pk), data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), "Voting already stopped")

        data = {"action": "tally"}
        response = self.client.put("/voting/{}/".format(voting.pk), data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), "Voting already tallied")

    def test_to_string(self):
        # Crea un objeto votacion
        v = self.create_voting()
        # Verifica que el nombre de la votacion es test voting
        self.assertEquals(str(v), "test voting")
        # Verifica que la descripcion de la pregunta sea test question
        self.assertEquals(str(v.question), "test question")
        # Verifica que la primera opcion es option1 (2)
        self.assertEquals(str(v.question.options.all()[0]), "option 1 (2)")

    def test_create_voting_API(self):
        self.login()
        data = {
            "name": "Example",
            "desc": "Description example",
            "question": "I want a ",
            "question_type": "DEFAULT",
            "question_opt": ["cat", "dog", "horse"],
        }

        response = self.client.post("/voting/", data, format="json")
        self.assertEqual(response.status_code, 201)

        voting = Voting.objects.get(name="Example")
        self.assertEqual(voting.desc, "Description example")


class LogInSuccessTests(StaticLiveServerTestCase):
    def setUp(self):
        # Load base test functionality for decide
        self.base = BaseTestCase()
        self.base.setUp()

        options = webdriver.ChromeOptions()
        options.headless = True
        self.driver = webdriver.Chrome(options=options)

        super().setUp()

    def tearDown(self):
        super().tearDown()
        self.driver.quit()

        self.base.tearDown()

    def successLogIn(self):
        self.cleaner.get(self.live_server_url + "/admin/login/?next=/admin/")
        self.cleaner.set_window_size(1280, 720)

        self.cleaner.find_element(By.ID, "id_username").click()
        self.cleaner.find_element(By.ID, "id_username").send_keys("decide")

        self.cleaner.find_element(By.ID, "id_password").click()
        self.cleaner.find_element(By.ID, "id_password").send_keys("decide")

        self.cleaner.find_element(By.ID, "id_password").send_keys("Keys.ENTER")
        self.assertTrue(self.cleaner.current_url == self.live_server_url + "/admin/")


class LogInErrorTests(StaticLiveServerTestCase):
    def setUp(self):
        # Load base test functionality for decide
        self.base = BaseTestCase()
        self.base.setUp()

        options = webdriver.ChromeOptions()
        options.headless = True
        self.driver = webdriver.Chrome(options=options)

        super().setUp()

    def tearDown(self):
        super().tearDown()
        self.driver.quit()

        self.base.tearDown()

    def usernameWrongLogIn(self):
        self.cleaner.get(self.live_server_url + "/admin/login/?next=/admin/")
        self.cleaner.set_window_size(1280, 720)

        self.cleaner.find_element(By.ID, "id_username").click()
        self.cleaner.find_element(By.ID, "id_username").send_keys("usuarioNoExistente")

        self.cleaner.find_element(By.ID, "id_password").click()
        self.cleaner.find_element(By.ID, "id_password").send_keys("usuarioNoExistente")

        self.cleaner.find_element(By.ID, "id_password").send_keys("Keys.ENTER")

        self.assertTrue(
            self.cleaner.find_element_by_xpath(
                "/html/body/div/div[2]/div/div[1]/p"
            ).text
            == "Please enter the correct username and password for a staff account. Note that both fields may be case-sensitive."
        )

    def passwordWrongLogIn(self):
        self.cleaner.get(self.live_server_url + "/admin/login/?next=/admin/")
        self.cleaner.set_window_size(1280, 720)

        self.cleaner.find_element(By.ID, "id_username").click()
        self.cleaner.find_element(By.ID, "id_username").send_keys("decide")

        self.cleaner.find_element(By.ID, "id_password").click()
        self.cleaner.find_element(By.ID, "id_password").send_keys("wrongPassword")

        self.cleaner.find_element(By.ID, "id_password").send_keys("Keys.ENTER")

        self.assertTrue(
            self.cleaner.find_element_by_xpath(
                "/html/body/div/div[2]/div/div[1]/p"
            ).text
            == "Please enter the correct username and password for a staff account. Note that both fields may be case-sensitive."
        )


class QuestionsTests(StaticLiveServerTestCase):
    def setUp(self):
        # Load base test functionality for decide
        self.base = BaseTestCase()
        self.base.setUp()

        options = webdriver.ChromeOptions()
        options.headless = True
        self.driver = webdriver.Chrome(options=options)

        super().setUp()

    def tearDown(self):
        super().tearDown()
        self.driver.quit()

        self.base.tearDown()

    def createQuestionSuccess(self):
        self.cleaner.get(self.live_server_url + "/admin/login/?next=/admin/")
        self.cleaner.set_window_size(1280, 720)

        self.cleaner.find_element(By.ID, "id_username").click()
        self.cleaner.find_element(By.ID, "id_username").send_keys("decide")

        self.cleaner.find_element(By.ID, "id_password").click()
        self.cleaner.find_element(By.ID, "id_password").send_keys("decide")

        self.cleaner.find_element(By.ID, "id_password").send_keys("Keys.ENTER")

        self.cleaner.get(self.live_server_url + "/admin/voting/question/add/")

        self.cleaner.find_element(By.ID, "id_desc").click()
        self.cleaner.find_element(By.ID, "id_desc").send_keys("Test")
        self.cleaner.find_element(By.ID, "id_options-0-number").click()
        self.cleaner.find_element(By.ID, "id_options-0-number").send_keys("1")
        self.cleaner.find_element(By.ID, "id_options-0-option").click()
        self.cleaner.find_element(By.ID, "id_options-0-option").send_keys("test1")
        self.cleaner.find_element(By.ID, "id_options-1-number").click()
        self.cleaner.find_element(By.ID, "id_options-1-number").send_keys("2")
        self.cleaner.find_element(By.ID, "id_options-1-option").click()
        self.cleaner.find_element(By.ID, "id_options-1-option").send_keys("test2")
        self.cleaner.find_element(By.NAME, "_save").click()

        self.assertTrue(
            self.cleaner.current_url == self.live_server_url + "/admin/voting/question/"
        )

    def createCensusEmptyError(self):
        self.cleaner.get(self.live_server_url + "/admin/login/?next=/admin/")
        self.cleaner.set_window_size(1280, 720)

        self.cleaner.find_element(By.ID, "id_username").click()
        self.cleaner.find_element(By.ID, "id_username").send_keys("decide")

        self.cleaner.find_element(By.ID, "id_password").click()
        self.cleaner.find_element(By.ID, "id_password").send_keys("decide")

        self.cleaner.find_element(By.ID, "id_password").send_keys("Keys.ENTER")

        self.cleaner.get(self.live_server_url + "/admin/voting/question/add/")

        self.cleaner.find_element(By.NAME, "_save").click()

        self.assertTrue(
            self.cleaner.find_element_by_xpath(
                "/html/body/div/div[3]/div/div[1]/div/form/div/p"
            ).text
            == "Please correct the errors below."
        )
        self.assertTrue(
            self.cleaner.current_url
            == self.live_server_url + "/admin/voting/question/add/"
        )


class VotingModelTestCase(BaseTestCase):
    def setUp(self):
        q = Question(desc="Descripcion")
        q.save()

        opt1 = QuestionOption(question=q, option="opcion 1")
        opt1.save()
        opt1 = QuestionOption(question=q, option="opcion 2")
        opt1.save()

        self.v = Voting(name="Votacion", question=q)
        self.v.save()


class QuestionTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        q = Question(desc="Descripcion")
        q.save()

        opt1 = QuestionOption(question=q, option="opcion 1")
        opt1.save()
        opt1 = QuestionOption(question=q, option="opcion 2")
        opt1.save()

        self.v = Voting(name="Votacion", question=q)
        self.v.save()

    def tearDown(self):
        super().tearDown()
        self.v = None
        Voting.objects.get(name="Votacion").delete()

    def testExist(self):
        v = Voting.objects.get(name="Votacion")
        self.assertEquals(v.question.options.all()[0].option, "opcion 1")

    def test_create_question(self):
        q = Question(desc="test question")
        q.save()
        self.assertEqual(q.desc, "test question")
        self.assertEqual(q.question_type, "DEFAULT")
        self.assertEqual(q.options.count(), 0)

    def test_create_question_yesno_from_api(self):
        data = {"desc": "test question", "question_type": "YESNO"}
        response = self.client.post("/voting/question/", data, format="json")
        self.assertEqual(response.status_code, 401)

        # login with user no admin
        self.login(user="noadmin")
        response = self.client.post("/voting/question/", data, format="json")
        self.assertEqual(response.status_code, 403)

        # login with user admin
        self.login()
        response = self.client.post("/voting/question/", data, format="json")
        self.assertEqual(response.status_code, 400)

        data = {"desc": "Description example", "question_type": "YESNO", "options": []}

        response = self.client.post("/voting/question/", data, format="json")
        self.assertEqual(response.status_code, 201)


class VotingRankingTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

    def tearDown(self):
        return super().tearDown()

    def create_ranking_voting(self):
        q = Question(desc="test ranking voting", question_type="RANKING")
        q.save()
        for i in range(1, 4):
            opt = QuestionOption(question=q, option="option {}".format(i))
            opt.save()
        v = Voting(name="test ranking voting", question=q)
        v.save()

        a, _ = Auth.objects.get_or_create(
            url=settings.BASEURL, defaults={"me": True, "name": "test auth"}
        )
        a.save()
        v.auths.add(a)
        return v

    def create_voters(self, v):
        for i in range(10):
            u, _ = User.objects.get_or_create(username="testRankingVoter{}".format(i))
            u.is_active = True
            u.save()
            c = Census(voter_id=u.id, voting_id=v.id)
            c.save()

    def get_or_create_user(self, pk):
        user, _ = User.objects.get_or_create(pk=pk)
        user.username = "user{}".format(pk)
        user.set_password("qwerty")
        user.save()
        return user

    def encrypt_msg(self, msg, v, bits=settings.KEYBITS):
        pk = v.pub_key
        p, g, y = (pk.p, pk.g, pk.y)
        k = MixCrypt(bits=bits)
        k.k = ElGamal.construct((p, g, y))
        return k.encrypt(msg)

    def store_votes(self, v):
        import random
        from Crypto.Util.number import bytes_to_long

        voters = list(Census.objects.filter(voting_id=v.id))
        voter = voters.pop()
        ranking_list = list(map(lambda o: o.number, v.question.options.all()))

        clear = {}
        for voter in voters:
            random.shuffle(ranking_list)
            key = int("".join(map(str, ranking_list)))

            if key in clear:
                clear[key] += 1
            else:
                clear[key] = 1

            message = int(key)
            a, b = self.encrypt_msg(message, v)
            data = {
                "voting": v.id,
                "voter": voter.voter_id,
                "vote": {"a": a, "b": b},
            }
            user = self.get_or_create_user(voter.voter_id)
            self.login(user=user.username)
            mods.post("store", json=data)

        return clear

    def test_ranking_voting(self):
        v = self.create_ranking_voting()
        self.create_voters(v)

        v.create_pubkey()
        v.start_date = timezone.now()
        v.save()

        clear = self.store_votes(v)

        self.login()  # set token
        v.tally_votes(self.token)

        tally = v.tally
        tally.sort()
        tally = {k: len(list(x)) for k, x in itertools.groupby(tally)}

        ranking = clear.keys()
        for order in ranking:
            self.assertEquals(tally.get(order, 0), clear.get(order, 0))

        postp = list(
            map(
                lambda o: str(o["number"]),
                sorted(v.postproc, key=lambda p: p["postproc"]),
            )
        )
        postp_selected = int("".join(postp))

        self.assertIn(postp_selected, list(tally.keys()))
        

class QuestionListTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='test', password='test', is_staff=True)
        self.client = Client()
        self.client.force_login(self.user)

    def test_get_with_staff_user(self):
        response = self.client.get('/voting/question/list/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'question_list.html')

    def test_get_with_non_staff_user(self):
        self.client.logout()
        response = self.client.get('/voting/question/list/')

        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, '403.html')
        

class QuestionCreationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpassword'
        )

    def test_get_question_creation_as_admin(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('question_creation'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'question_creation.html')
        self.assertIsInstance(response.context['form'], QuestionForm)
        self.assertIsInstance(response.context['formset'], QuestionOptionFormSet)

    def test_get_question_creation_as_non_admin(self):
        response = self.client.get(reverse('question_creation'))
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, '403.html')

    def test_post_question_creation_as_admin(self):
        self.client.force_login(self.admin_user)
        data = {
            'desc': 'Sample question',
            'question_type': 'YESNO',
        }
        form = QuestionForm(data)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(Question.objects.count(), 1)

    def test_post_question_creation_as_non_admin(self):
        data = {
            'desc': 'Sample question',
            'question_type': 'YESNO',
        }
        response = self.client.post(reverse('question_creation'), data)
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, '403.html')
        self.assertEqual(Question.objects.count(), 0)
        self.assertEqual(QuestionOption.objects.count(), 0)
        
class QuestionDeleteViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpassword'
        )
        self.question = Question.objects.create(desc='Test question')

    def test_question_delete_post(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(reverse('question_delete', args=[self.question.id]))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('question_list'))
        self.assertFalse(Question.objects.filter(pk=self.question.id).exists())

    def test_question_delete_post_unauthorized(self):
        response = self.client.post(reverse('question_delete', args=[self.question.id]))

        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, '403.html')
        self.assertTrue(Question.objects.filter(pk=self.question.id).exists())

    def test_question_delete_post_nonexistent_question(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(reverse('question_delete', args=[999]))

        self.assertEqual(response.status_code, 404)
        
class VotingListTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='test', password='test', is_staff=True)
        self.client = Client()
        self.client.force_login(self.user)

    def test_get_with_staff_user(self):
        response = self.client.get('/voting/list/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'voting_list.html')

    def test_get_with_non_staff_user(self):
        self.client.logout()
        response = self.client.get('/voting/list/')

        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, '403.html')
        
class VotingActionsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='admin', password='admin')
        q = Question(desc="Descripcion")
        q.save()

        opt1 = QuestionOption(question=q, option="opcion 1")
        opt1.save()
        opt1 = QuestionOption(question=q, option="opcion 2")
        opt1.save()

        self.voting = Voting(name="Votacion", question=q)
        self.voting.save()
    
    def test_start_voting_as_admin(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('voting_start', args=[self.voting.id]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('voting_list'))
        self.voting.refresh_from_db()
        self.assertIsNotNone(self.voting.start_date)

    def test_start_voting_as_non_admin(self):
        response = self.client.post(reverse('voting_start', args=[self.voting.id]))
        self.assertEqual(response.status_code, 403)

    def test_stop_voting_as_admin(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('voting_stop', args=[self.voting.id]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('voting_list'))
        self.voting.refresh_from_db()
        self.assertIsNotNone(self.voting.end_date)

    def test_stop_voting_as_non_admin(self):
        response = self.client.post(reverse('voting_stop', args=[self.voting.id]))
        self.assertEqual(response.status_code, 403)