from base.models import Auth
from base.tests import BaseTestCase
from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.utils import timezone

from selenium import webdriver
from selenium.webdriver.common.by import By
from voting.models import Question, Voting, QuestionOption


class VisualizerTestCase(StaticLiveServerTestCase):
    def create_votings(self):
        q = Question(desc="Pregunta prueba")
        q.save()
        for i in range(3):
            opt = QuestionOption(question=q, option="opción {}".format(i + 1))
            opt.save()
        voting_open = Voting(
            name="Pregunta prueba", question=q, start_date=timezone.now()
        )
        voting_open.save()
        voting_closed = Voting(
            name="test voting closed", question=q, start_date=timezone.now()
        )
        voting_closed.save()
        voting_not_started = Voting(name="test voting not started", question=q)
        voting_not_started.save()
        auth, _ = Auth.objects.get_or_create(
            url=settings.BASEURL, defaults={"me": True, "name": "test auth"}
        )
        auth.save()
        voting_open.auths.add(auth)
        voting_closed.auths.add(auth)
        voting_not_started.auths.add(auth)
        # Close voting
        voting_closed.end_date = timezone.now()
        voting_closed.save()
        return voting_open, voting_closed, voting_not_started

    def setUp(self):
        (
            self.voting_open,
            self.voting_closed,
            self.voting_not_started,
        ) = self.create_votings()
        # Selenium Setup
        self.base = BaseTestCase()
        self.base.setUp()
        # Opciones de Chrome
        options = webdriver.ChromeOptions()
        options.headless = True
        self.driver = webdriver.Chrome(options=options)
        super().setUp()

    def tearDown(self):
        super().tearDown()
        self.driver.quit()
        self.base.tearDown()

    def test_votacion_abierta(self):
        # Ruta navegador
        self.driver.get(f"{self.live_server_url}/visualizer/{self.voting_open.id}")
        self.assertTrue(len(self.driver.find_elements(By.ID, "app-visualizer")) == 1)
        self.assertTrue(
            len(
                self.driver.find_elements(
                    By.XPATH, "//*[contains(text(), 'Votación en curso')]"
                )
            )
            == 1
        )  # Verifica si votación abierta (si esta bierta da 1)

    def test_votacion_no_empezada(self):
        self.driver.get(
            f"{self.live_server_url}/visualizer/{self.voting_not_started.id}"
        )
        self.assertTrue(len(self.driver.find_elements(By.ID, "app-visualizer")) == 1)
        self.assertTrue(
            len(
                self.driver.find_elements(
                    By.XPATH, "//*[contains(text(), 'Votación no comenzada')]"
                )
            )
            == 1
        )  # Verifica q votación no comenzado

    def test_votacion_cerrada(self):
        self.driver.get(f"{self.live_server_url}/visualizer/{self.voting_closed.id}")
        self.assertTrue(len(self.driver.find_elements(By.ID, "app-visualizer")) == 1)
        self.assertTrue(
            len(self.driver.find_elements(By.CLASS_NAME, "chart-container")) == 2
        )
        self.assertTrue(len(self.driver.find_elements(By.ID, "scoreChart")) == 1)
        self.assertTrue(len(self.driver.find_elements(By.ID, "votesChart")) == 1)
