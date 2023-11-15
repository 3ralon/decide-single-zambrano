from rest_framework.response import Response
from rest_framework.status import (
        HTTP_200_OK,
        HTTP_201_CREATED,
        HTTP_400_BAD_REQUEST,
        HTTP_401_UNAUTHORIZED
)
from django.http import HttpResponseRedirect
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from django.shortcuts import redirect, render
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from allauth.socialaccount.models import SocialAccount

from .serializers import UserSerializer


class GetUserView(APIView):
    def post(self, request):
        key = request.data.get('token', '')
        tk = get_object_or_404(Token, key=key)
        return Response(UserSerializer(tk.user, many=False).data)


class LogoutView(APIView):
    def post(self, request):
        key = request.data.get('token', '')
        try:
            tk = Token.objects.get(key=key)
            tk.delete()
        except ObjectDoesNotExist:
            pass

        return Response({})


class RegisterView(APIView):
    
    def handle_google_login(self, request):

        # Comprobar si es la primera vez que el usuario se logea con google
        social_account = SocialAccount.objects.filter(user=request.user, provider='google').first()
        if social_account is None:
            # Creamos un nuevo usuario django para esta cuenta de google
            social_account = SocialAccount.objects.create(user=request.user, provider='google')
            social_account.save()
            return Response({'user_pk': social_account.user.pk, 'token': social_account.user.token.key}, status=HTTP_201_CREATED)

        login(request, request.user)

        return Response({'message': 'Login successful', 'user_pk':request.user.pk, 'token': request.user.token.key}, status=HTTP_200_OK)
    
    def post(self, request):
        # Verificar si el usuario que hace la solicitud es un superusuario o un usuario normal
        is_superuser = request.user.is_superuser

        # Si no es un superusuario, manejar el registro del usuario normal
        if not is_superuser:
            if request.POST.get('provider') == 'google':
                return self.handle_google_login(request)
            
            form = UserCreationForm(request.data)
            if form.is_valid():
                user = form.save()
                token, _ = Token.objects.get_or_create(user=user)
                HttpResponseRedirect('/', status=HTTP_201_CREATED)
                return Response({'user_pk': user.pk, 'token': token.key}, status=HTTP_201_CREATED)
            else:
                return Response(form.errors, status=HTTP_400_BAD_REQUEST)

        # Si es un superusuario, manejar el registro del administrador
        username = request.data.get('username', '')
        pwd = request.data.get('password', '')

        if not username or not pwd:
            return Response({}, status=HTTP_400_BAD_REQUEST)

        try:
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_password(pwd)
                user.save()
                token, _ = Token.objects.get_or_create(user=user)
                return Response({'user_pk': user.pk, 'token': token.key}, status=HTTP_201_CREATED)
            else:
                return Response({'error': 'User already exists'}, status=HTTP_400_BAD_REQUEST)
        
        except IntegrityError:
            return Response({}, status=HTTP_400_BAD_REQUEST)

    def get(self, request):
        form = UserCreationForm()
        return render(request, 'registration_form.html', {'form': form})
