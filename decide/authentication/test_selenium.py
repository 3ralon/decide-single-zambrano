from django.test import TestCase
from django.db import connection
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from base.tests import BaseTestCase
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from django.contrib.auth.models import User
from selenium.webdriver.support.ui import WebDriverWait
from django.contrib.sites.models import Site
from django.contrib.sites.models import Site
from django.contrib.sites.shortcuts import get_current_site
from allauth.socialaccount.models import SocialApp
from django.db import models
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp


class AdminTestCase(StaticLiveServerTestCase):
    def setUp(self):
        # Crea un usuario admin y otro no admin
        self.base = BaseTestCase()
        self.base.setUp()

        # Opciones de Chrome
        options = webdriver.ChromeOptions()
        options.headless = False
        self.driver = webdriver.Chrome(options=options)

        super().setUp()

    def tearDown(self):
        super().tearDown()
        self.driver.quit()

        self.base.tearDown()

    def test_simpleCorrectLogin(self):
        # Abre la ruta del navegador
        self.driver.get(f"{self.live_server_url}/admin/")
        # Busca los elementos y “escribe”
        self.driver.find_element(By.ID, "id_username").send_keys("admin")
        self.driver.find_element(By.ID, "id_password").send_keys("qwerty", Keys.ENTER)

        # Verifica que nos hemos logado porque aparece la barra de herramientas superior
        self.assertTrue(len(self.driver.find_elements(By.ID, "user-tools")) == 1)

    def test_simpleWrongLogin(self):
        self.driver.get(f"{self.live_server_url}/admin/")
        self.driver.find_element(By.ID, "id_username").send_keys("WRONG")
        self.driver.find_element(By.ID, "id_password").send_keys("WRONG")
        self.driver.find_element(By.ID, "login-form").submit()

        # Si no, aparece este error
        self.assertTrue(len(self.driver.find_elements(By.CLASS_NAME, "errornote")) == 1)
        time.sleep(5)
        
class RegistrationTestCase(StaticLiveServerTestCase):
    
    def setUp(self):
        self.base = BaseTestCase()
        self.base.setUp()

        options = webdriver.ChromeOptions()
        options.headless = False
        options.add_argument("--no-sandbox")
        self.driver = webdriver.Chrome(options=options)
        self.user = User.objects.create_user(username="testuser", password="testpass")

        current_site = get_current_site(self.driver)
        print(current_site)
        
        app = SocialApp.objects.create(
            provider="Google",
            name="google",
            client_id="test",
            secret="test",
        )
        app.sites.add(current_site)
        
        super().setUp()
        
    def tearDown(self):
        super().tearDown()
        self.driver.quit()
        self.base.tearDown()
        


    def test_simpleCorrectRegistration(self):
        
        self.driver.get("http://localhost:8000/authentication/register/")
        #self.driver.get(f"{self.live_server_url}/authentication/register/")
        time.sleep(10)
        username_input = self.driver.find_element(By.ID, "id_username")
        username_input.send_keys("testuser")
        password_input = self.driver.find_element(By.ID, "id_password1")
        password_input.send_keys("D0z29'RM<I4m")
        password_confirm_input = self.driver.find_element(By.ID, "id_password2")
        password_confirm_input.send_keys("D0z29'RM<I4m")

        # Submit the form
        time.sleep(10)
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # Check if a new user was created with the correct username and password
        self.assertEqual(User.objects.count(), 3)
        user = User.objects.get(username="testuser")
        self.assertTrue(user.check_password("D0z29'RM<I4m"))
        
    

class GoogleLoginTestCase(StaticLiveServerTestCase):
    def setUp(self):
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