from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone

from base.tests import BaseTestCase
from mixnet.models import Auth
from voting.models import Voting, Question, QuestionOption
from census.models import Census


class BoothTestCase(BaseTestCase):
    def setUp(self):

        # Auth para votings
        auth, _ = Auth.objects.get_or_create(
            url=settings.BASEURL, defaults={"me": True, "name": "test auth"}
        )
        auth.save()

        # Default
        default_question = Question(desc="Pregunta default")
        default_question.save()
        for i in range(3):
            opt = QuestionOption(
                question=default_question, option="opción default {}".format(i + 1)
            )
            opt.save()

        default_voting = Voting(
            name="Votación default",
            question=default_question,
            start_date=timezone.now(),
        )
        default_voting.save()
        default_voting.auths.add(auth)

        self.default_voting = default_voting

        super().setUp()

    def tearDown(self):
        self.client.logout()
        self.default_voting.delete()
        super().tearDown()

    def testBoothNotFound(self):
        # Se va a probar con el numero 10000 pues en las condiciones actuales en las que nos encontramos no parece posible que se genren 10000 votaciones diferentes
        admin = User.objects.get(username="admin")
        self.client.force_login(user=admin)
        response = self.client.get("/booth/vote/10000/")
        self.assertEqual(response.status_code, 404)

    def testBoothRedirection(self):
        # Se va a probar con el numero 10000 pues en las condiciones actuales en las que nos encontramos no parece posible que se genren 10000 votaciones diferentes
        response = self.client.get("/booth/vote/10000")
        self.assertEqual(response.status_code, 301)

    def testHomepage(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Decide")

    def test_check_fail_census_before_vote(self):
        admin = User.objects.get(username="admin")
        self.client.force_login(user=admin)
        response = self.client.get(f"/booth/vote/{self.default_voting.id}/")
        self.assertEqual(response.status_code, 401)

    def test_check_success_census_before_vote(self):
        self.default_voting.create_pubkey()
        admin = User.objects.get(username="admin")
        census = Census(voting_id=self.default_voting.id, voter_id=admin.id)
        census.save()

        self.client.force_login(user=admin)
        response = self.client.get(f"/booth/vote/{self.default_voting.id}/")
        self.assertEqual(response.status_code, 200)
