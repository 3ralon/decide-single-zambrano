import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.auth.models import User
from django.utils import timezone
from base.models import Auth
from voting.models import Question, Voting, QuestionOption
from django.conf import settings
from base.tests import BaseTestCase
from selenium.webdriver.chrome.options import Options
class CSVExportTest(StaticLiveServerTestCase):

    def create_voting(self):
        q = Question(desc="Pregunta prueba")
        q.save()

        for i in range(3):
            opt = QuestionOption(question=q, option="opción {}".format(i + 1))
            opt.save()

        voting = Voting(name="Pregunta prueba", question=q, start_date=timezone.now())
        voting.save()

        auth, _ = Auth.objects.get_or_create(
            url=settings.BASEURL, defaults={"me": True, "name": "test auth"}
        )
        auth.save()
        voting.auths.add(auth)

        return voting

    def setUp(self):
        self.base = BaseTestCase()
        self.base.setUp()

        # Set up the download directory for files
        self.download_dir = os.path.join(os.path.dirname(__file__), 'downloads')
        os.makedirs(self.download_dir, exist_ok=True)

        # Set up Chrome options
        options = webdriver.ChromeOptions()
        options.headless = True
        options.add_experimental_option('prefs', {
            "download.default_directory": self.download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True
        })

        self.driver = webdriver.Chrome(options=options)

        try:
            self.superuser = User.objects.get(username='test')
        except User.DoesNotExist:
            self.superuser = User.objects.create_superuser('test', 'admin@example.com', 'test')

        # Navigate to the login page
        self.driver.get(f'{self.live_server_url}/admin/')

        # Fill in the login form and submit it
        self.driver.find_element(By.ID, 'id_username').send_keys("test")
        self.driver.find_element(By.ID, 'id_password').send_keys("test", Keys.ENTER)

        # Create a voting
        self.voting = self.create_voting()
        self.assertIsNotNone(self.voting.id)  # Ensure the voting was created

        super().setUp()
        

    def tearDown(self):
        super().tearDown()
        self.driver.quit()
        self.base.tearDown()

    def wait_for_element(self, by, value, timeout=10):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )

    def wait_for_file_to_download(self, file_path, timeout=30):
        # Wait until the file is downloaded
        for _ in range(timeout):
            if os.path.exists(file_path):
                return
            time.sleep(1)
        raise TimeoutError(f"The file did not download within {timeout} seconds.")
    #Test para la exportatión de todos los censos
    def test_export_all_csv(self):
        self.driver.get(f"{self.live_server_url}/census/descargar-csv/")  

        # Wait for the "Exportar CSV completo" button to be present before clicking
        submit_button = self.wait_for_element(By.ID, 'submit-all')
        submit_button.click()

        file_path = os.path.join(self.download_dir, 'CensoCompleto.csv')

        # Wait for the file to be downloaded
        self.wait_for_file_to_download(file_path)

        self.assertTrue(os.path.exists(file_path))

    def test_export_specific_csv(self):
        self.driver.get(f"{self.live_server_url}/census/descargar-csv/")  

        # Wait for the "Exportar a votación a CSV" button to be present before interacting
        voting_id_field = self.wait_for_element(By.ID, 'voting_id')
        voting_id_field.send_keys(self.voting.id)

        # Wait for the button to be present before clicking
        submit_button = self.wait_for_element(By.ID, 'submit-specific')
        submit_button.click()

        file_path = os.path.join(self.download_dir, f'Censo_{self.voting.id}.csv')

        # Wait for the file to be downloaded
        self.wait_for_file_to_download(file_path)

        self.assertTrue(os.path.exists(file_path))


