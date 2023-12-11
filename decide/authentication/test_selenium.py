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
from selenium.common.exceptions import NoSuchElementException


class AdminTestCase(StaticLiveServerTestCase):
    
    def setUp(self):
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

        # Opciones de Chrome
        options = webdriver.ChromeOptions()
        options.headless = False
        self.driver = webdriver.Chrome(options=options)

        super().setUp()

    def tearDown(self):
        super().tearDown()
        self.driver.quit()

        self.base.tearDown()

    def test_simpleCorrectRegistration(self):
        
        self.driver.get(f"{self.live_server_url}/authentication/register/")
        username_input = self.driver.find_element(By.ID, "id_username")
        username_input.send_keys("testuser")
        password_input = self.driver.find_element(By.ID, "id_password1")
        password_input.send_keys("D0z29'RM<I4m")
        password_confirm_input = self.driver.find_element(By.ID, "id_password2")
        password_confirm_input.send_keys("D0z29'RM<I4m")

        # enviar el formulario
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # Comprobar que se ha creado el usuario
        self.assertEqual(User.objects.count(), 3)
        user = User.objects.get(username="testuser")
        self.assertTrue(user.check_password("D0z29'RM<I4m"))

    def test_weakPasswordRegistration(self):
        self.driver.get(f"{self.live_server_url}/authentication/register/")

        username_input = self.driver.find_element(By.ID, "id_username")
        username_input.send_keys("weakpassworduser")
        password_input = self.driver.find_element(By.ID, "id_password1")
        password_input.send_keys("weak")
        password_confirm_input = self.driver.find_element(By.ID, "id_password2")
        password_confirm_input.send_keys("weak")

        # enviar el formulario
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # Comprobar que se muestra un mensaje de error de contraseña débil
        self.assertTrue("This password is too short. It must contain at least 8 characters" in self.driver.page_source)

    def test_passwordMismatchRegistration(self):
        self.driver.get(f"{self.live_server_url}/authentication/register/")
        username_input = self.driver.find_element(By.ID, "id_username")
        username_input.send_keys("mismatchuser")
        password_input = self.driver.find_element(By.ID, "id_password1")
        password_input.send_keys("Mismatch123!")
        password_confirm_input = self.driver.find_element(By.ID, "id_password2")
        password_confirm_input.send_keys("Mismatch456!")

        # enviar el formulario
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # Comprobar que se muestra un mensaje de error de coincidencia de contraseña
        self.assertTrue("The two password fields didn’t match" in self.driver.page_source)
        
    def test_userAlreadyExists(self):
        self.driver.get(f"{self.live_server_url}/authentication/register/")
        username_input = self.driver.find_element(By.ID, "id_username")
        username_input.send_keys("admin")
        password_input = self.driver.find_element(By.ID, "id_password1")
        password_input.send_keys("D0z29'RM<I4m")
        password_confirm_input = self.driver.find_element(By.ID, "id_password2")
        password_confirm_input.send_keys("D0z29'RM<I4m")

        # enviar el formulario
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # Comprobar que se muestra un mensaje de error de coincidencia de contraseña
        self.assertTrue("A user with that username already exists" in self.driver.page_source)
        
    def test_blankFieldRegistration(self):
        self.driver.get(f"{self.live_server_url}/authentication/register/")

        # Dejamos el nombre de usuario en blanco
        password_input = self.driver.find_element(By.ID, "id_password1")
        password_input.send_keys("Password123!")
        password_confirm_input = self.driver.find_element(By.ID, "id_password2")
        password_confirm_input.send_keys("Password123!")

        # enviar el formulario
        self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # Comprobamos que sigue el formulario de registro
        self.assertTrue("Register" in self.driver.page_source)
        self.assertTrue("id_username" in self.driver.page_source)
        self.assertTrue("id_password1" in self.driver.page_source)
        self.assertTrue("id_password2" in self.driver.page_source)