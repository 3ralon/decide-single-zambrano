from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

from .models import Census
from base import mods
from base.tests import BaseTestCase
from datetime import datetime
from django.urls import reverse
from django.test import RequestFactory
from census.views import CensusExportationToCSV


class CensusTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.census = Census(voting_id=1, voter_id=1)
        self.census.save()

    def tearDown(self):
        super().tearDown()
        self.census = None

    def test_check_vote_permissions(self):
        response = self.client.get(
            "/census/{}/?voter_id={}".format(1, 2), format="json"
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), "Invalid voter")

        response = self.client.get(
            "/census/{}/?voter_id={}".format(1, 1), format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), "Valid voter")

    def test_list_voting(self):
        response = self.client.get("/census/?voting_id={}".format(1), format="json")
        self.assertEqual(response.status_code, 401)

        self.login(user="noadmin")
        response = self.client.get("/census/?voting_id={}".format(1), format="json")
        self.assertEqual(response.status_code, 403)

        self.login()
        response = self.client.get("/census/?voting_id={}".format(1), format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"voters": [1]})

    def test_add_new_voters_conflict(self):
        data = {"voting_id": 1, "voters": [1]}
        response = self.client.post("/census/", data, format="json")
        self.assertEqual(response.status_code, 401)

        self.login(user="noadmin")
        response = self.client.post("/census/", data, format="json")
        self.assertEqual(response.status_code, 403)

        self.login()
        response = self.client.post("/census/", data, format="json")
        self.assertEqual(response.status_code, 409)

    def test_add_new_voters(self):
        data = {"voting_id": 2, "voters": [1, 2, 3, 4]}
        response = self.client.post("/census/", data, format="json")
        self.assertEqual(response.status_code, 401)

        self.login(user="noadmin")
        response = self.client.post("/census/", data, format="json")
        self.assertEqual(response.status_code, 403)

        self.login()
        response = self.client.post("/census/", data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(data.get("voters")), Census.objects.count() - 1)

    def test_destroy_voter(self):
        data = {"voters": [1]}
        response = self.client.delete("/census/{}/".format(1), data, format="json")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(0, Census.objects.count())


class CensusExportationTests(BaseTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_get_unauthenticated_export_to_csv(self):
        response = self.client.get(reverse("export_page"))
        self.assertEqual(response.status_code, 403)
        response = self.client.post(reverse("export_page"))
        self.assertEqual(response.status_code, 403)

    def test_get_export_to_csv(self):
        # Para un usuario que no es superuser
        user = User.objects.create_user("testuser", "testuser")
        request = self.factory.get("census/descargar-csv/")
        request.user = user
        response = CensusExportationToCSV.as_view()(request)
        self.assertEqual(response.status_code, 403)
        # Para un usuario que sí es superuser
        user = User.objects.create_superuser(
            "testadmin", "admin@example.com", "testadmin"
        )
        request = self.factory.get("census/descargar-csv/")
        request.user = user
        response = CensusExportationToCSV.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_post_descargar_csv(self):
        # Para un usuario que no es superuser
        user = User.objects.create_user("testuser", "testuser")
        request = self.factory.post("census/descargar-csv/")
        request.user = user
        response = CensusExportationToCSV.as_view()(request)
        self.assertEqual(response.status_code, 403)
        # Para un usuario que sí es superuser
        user = User.objects.create_superuser(
            "testadmin", "admin@example.com", "testadmin"
        )
        request = self.factory.post("census/descargar-csv/")
        request.user = user
        response = CensusExportationToCSV.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_post_request_superuser_export_one_csv(self):
        # Para un usuario que sí es staff ni superuser
        user = User.objects.create_superuser(
            "testadmin", "admin@example.com", "testadmin"
        )
        request = self.factory.post("census/export-to-csv/", {"voting_id": 1})
        request.user = user
        response = CensusExportationToCSV.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")

    def test_post_request_unauthorized_export_one_csv(self):
        # Para un usuario que no es staff ni superuser
        user = User.objects.create_user("testuser", "testuser")
        request = self.factory.post("census/export-to-csv/", {"voting_id": 1})
        request.user = user
        response = CensusExportationToCSV.as_view()(request)
        self.assertEqual(response.status_code, 403)

    def test_post_request_superuser_export_all(self):
        # Para un usuario que sí es staff ni superuser
        user = User.objects.create_superuser(
            "testadmin", "admin@example.com", "testadmin"
        )
        request = self.factory.post("census/export-all-census/")
        request.user = user
        response = CensusExportationToCSV.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")

    def test_post_request_unauthorized_export_all(self):
        # Para un usuario que no es staff ni superuser
        user = User.objects.create_user("testuser", "testuser")
        request = self.factory.post("census/export-all-census/")
        request.user = user
        response = CensusExportationToCSV.as_view()(request)
        self.assertEqual(response.status_code, 403)


class CensusTest(StaticLiveServerTestCase):
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

    def createCensusSuccess(self):
        self.cleaner.get(self.live_server_url + "/admin/login/?next=/admin/")
        self.cleaner.set_window_size(1280, 720)

        self.cleaner.find_element(By.ID, "id_username").click()
        self.cleaner.find_element(By.ID, "id_username").send_keys("decide")

        self.cleaner.find_element(By.ID, "id_password").click()
        self.cleaner.find_element(By.ID, "id_password").send_keys("decide")

        self.cleaner.find_element(By.ID, "id_password").send_keys("Keys.ENTER")

        self.cleaner.get(self.live_server_url + "/admin/census/census/add")
        now = datetime.now()
        self.cleaner.find_element(By.ID, "id_voting_id").click()
        self.cleaner.find_element(By.ID, "id_voting_id").send_keys(
            now.strftime("%m%d%M%S")
        )
        self.cleaner.find_element(By.ID, "id_voter_id").click()
        self.cleaner.find_element(By.ID, "id_voter_id").send_keys(
            now.strftime("%m%d%M%S")
        )
        self.cleaner.find_element(By.NAME, "_save").click()

        self.assertTrue(
            self.cleaner.current_url == self.live_server_url + "/admin/census/census"
        )

    def createCensusEmptyError(self):
        self.cleaner.get(self.live_server_url + "/admin/login/?next=/admin/")
        self.cleaner.set_window_size(1280, 720)

        self.cleaner.find_element(By.ID, "id_username").click()
        self.cleaner.find_element(By.ID, "id_username").send_keys("decide")

        self.cleaner.find_element(By.ID, "id_password").click()
        self.cleaner.find_element(By.ID, "id_password").send_keys("decide")

        self.cleaner.find_element(By.ID, "id_password").send_keys("Keys.ENTER")

        self.cleaner.get(self.live_server_url + "/admin/census/census/add")

        self.cleaner.find_element(By.NAME, "_save").click()

        self.assertTrue(
            self.cleaner.find_element_by_xpath(
                "/html/body/div/div[3]/div/div[1]/div/form/div/p"
            ).text
            == "Please correct the errors below."
        )
        self.assertTrue(
            self.cleaner.current_url
            == self.live_server_url + "/admin/census/census/add"
        )

    def createCensusValueError(self):
        self.cleaner.get(self.live_server_url + "/admin/login/?next=/admin/")
        self.cleaner.set_window_size(1280, 720)

        self.cleaner.find_element(By.ID, "id_username").click()
        self.cleaner.find_element(By.ID, "id_username").send_keys("decide")

        self.cleaner.find_element(By.ID, "id_password").click()
        self.cleaner.find_element(By.ID, "id_password").send_keys("decide")

        self.cleaner.find_element(By.ID, "id_password").send_keys("Keys.ENTER")

        self.cleaner.get(self.live_server_url + "/admin/census/census/add")
        now = datetime.now()
        self.cleaner.find_element(By.ID, "id_voting_id").click()
        self.cleaner.find_element(By.ID, "id_voting_id").send_keys("64654654654654")
        self.cleaner.find_element(By.ID, "id_voter_id").click()
        self.cleaner.find_element(By.ID, "id_voter_id").send_keys("64654654654654")
        self.cleaner.find_element(By.NAME, "_save").click()

        self.assertTrue(
            self.cleaner.find_element_by_xpath(
                "/html/body/div/div[3]/div/div[1]/div/form/div/p"
            ).text
            == "Please correct the errors below."
        )
        self.assertTrue(
            self.cleaner.current_url
            == self.live_server_url + "/admin/census/census/add"
        )
