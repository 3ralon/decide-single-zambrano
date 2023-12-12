from rest_framework.test import APIClient
from rest_framework.test import APITestCase
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from base import mods

class AuthTestCase(APITestCase):

    def setUp(self):
        self.client = APIClient()
        mods.mock_query(self.client)
        u = User(username='voter1')
        u.set_password('123')
        u.save()

        u2 = User(username='admin')
        u2.set_password('admin')
        u2.is_superuser = True
        u2.save()

    def tearDown(self):
        self.client = None

    def test_login(self):
        data = {'username': 'voter1', 'password': '123'}
        response = self.client.post('/authentication/login/', data, format='json')
        self.assertEqual(response.status_code, 200)

        token = response.json()
        self.assertTrue(token.get('token'))

    def test_login_fail(self):
        data = {'username': 'voter1', 'password': '321'}
        response = self.client.post('/authentication/login/', data, format='json')
        self.assertEqual(response.status_code, 400)

    def test_getuser(self):
        data = {'username': 'voter1', 'password': '123'}
        response = self.client.post('/authentication/login/', data, format='json')
        self.assertEqual(response.status_code, 200)
        token = response.json()

        response = self.client.post('/authentication/getuser/', token, format='json')
        self.assertEqual(response.status_code, 200)

        user = response.json()
        self.assertEqual(user['id'], 1)
        self.assertEqual(user['username'], 'voter1')

    def test_getuser_invented_token(self):
        token = {'token': 'invented'}
        response = self.client.post('/authentication/getuser/', token, format='json')
        self.assertEqual(response.status_code, 404)

    def test_getuser_invalid_token(self):
        data = {'username': 'voter1', 'password': '123'}
        response = self.client.post('/authentication/login/', data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Token.objects.filter(user__username='voter1').count(), 1)

        token = response.json().get('token')
        self.assertTrue(token)

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)
        response = self.client.post('/authentication/logout/')
        self.assertEqual(response.status_code, 200)

        # Clear the credentials
        self.client.credentials()

        # Try to get user information with the old token
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)
        response = self.client.post('/authentication/getuser/')
        self.assertEqual(response.status_code, 404)

    def test_logout(self):
       
        data = {'username': 'voter1', 'password': '123'}
        response = self.client.post('/authentication/login/', data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Token.objects.filter(user__username='voter1').count(), 1)
       
        token = response.json()
        self.assertTrue(token.get('token'))
        response = self.client.post('/authentication/logout/', token, format='json')
        self.assertEqual(response.status_code, 200)
        

    def test_register_bad_request(self):
        data = {'username': 'admin', 'password': 'admin'}
        response = self.client.post('/authentication/login/', data, format='json')
        self.assertEqual(response.status_code, 200)
        token = response.json()
        token.update({'username': 'user1'})
        user_count_before = User.objects.count()
        self.client.post('/authentication/register/', token, format='json')
        
        user_count_after = User.objects.count()
        self.assertEqual(user_count_after, user_count_before)

    def test_register_user_already_exist(self):
        data = {'username': 'admin', 'password': 'admin'}
        response = self.client.post('/authentication/login/', data, format='json')
        self.assertEqual(response.status_code, 200)
        token = response.json()
        token.update(data)
        user_count_before = User.objects.count()
        self.client.post('/authentication/register/', token, format='json')
        
        user_count_after = User.objects.count()
        self.assertEqual(user_count_after, user_count_before)

    def test_register_from_admin(self):
        data = {'username': 'admin', 'password': 'admin'}
        response = self.client.post('/authentication/login/', data, format='json')
        self.assertEqual(response.status_code, 200)
        token = response.json()

        token.update({'username': 'user1', 'password1': 'pwd123456789', 'password2': 'pwd123456789'})
        response = self.client.post('/authentication/register/', token, format='json')
        self.assertEqual(response.status_code, 201)

    def test_register_from_user(self):
        data = {'username': 'new_user', 'password1': 'new_password', 'password2': 'new_password'}
        response = self.client.post('/authentication/register/', data, format='json')
        self.assertEqual(response.status_code, 201) 
        response_data = response.json()
        self.assertTrue('token' in response_data)
        self.assertTrue('user_pk' in response_data)

        login_data = {'username': 'new_user', 'password': 'new_password'}
        response = self.client.post('/authentication/login/', login_data, format='json')
        self.assertEqual(response.status_code, 200)
        token = response.json()
        self.assertTrue('token' in token)
        
    def test_only_one_password(self):
        data = {'username': 'new_user', 'password1': 'new_password'}
        user_count_before = User.objects.count()
        self.client.post('/authentication/register/', data, format='json')
        
        user_count_after = User.objects.count()
        self.assertEqual(user_count_after, user_count_before)
        
    def test_password_not_match(self):
        data = {'username': 'new_user', 'password1': 'new_password', 'password2': 'new_password2'}
        user_count_before = User.objects.count()
        self.client.post('/authentication/register/', data, format='json')
        
        user_count_after = User.objects.count()
        self.assertEqual(user_count_after, user_count_before)
        
    def test_password_too_short(self):
        data = {'username': 'new_user', 'password1': 'new', 'password2': 'new'}
        user_count_before = User.objects.count()
        self.client.post('/authentication/register/', data, format='json')
        
        user_count_after = User.objects.count()
        self.assertEqual(user_count_after, user_count_before)
        
    def test_password_same_username(self):
        data = {'username': 'new_user', 'password1': 'new_user', 'password2': 'new_user'}
        user_count_before = User.objects.count()
        self.client.post('/authentication/register/', data, format='json')
        
        user_count_after = User.objects.count()
        self.assertEqual(user_count_after, user_count_before)
        
        
    def test_password_too_common(self):
        data = {'username': 'new_user', 'password1': 'password', 'password2': 'password'}
        user_count_before = User.objects.count()
        self.client.post('/authentication/register/', data, format='json')
        
        user_count_after = User.objects.count()
        self.assertEqual(user_count_after, user_count_before)
