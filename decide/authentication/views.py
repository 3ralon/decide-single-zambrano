from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
)
from django.contrib.auth import logout
from django.http import JsonResponse
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from django.shortcuts import redirect, render
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from allauth.socialaccount.models import SocialAccount
from rest_framework.authtoken.models import Token
from .forms import LoginForm
from django.views.generic import TemplateView

from .serializers import UserSerializer


class LoginView(TemplateView):
    template_name = "log_in.html"

    def post(self, request):
        form = LoginForm(request.POST)

        mensaje = None

        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            remember_me = form.cleaned_data.get("remember_me")
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)

                if not remember_me:
                    request.session.set_expiry(0)

                next_url = request.GET.get("next", None)
                if next_url:
                    return redirect(next_url)
                return redirect("/")
            else:
                mensaje = "Credenciales incorrectas"
        else:
            mensaje = "Error al inicar sesión"

        return render(request, "log_in.html", {"form": form, "mensaje": mensaje})


class GetUserView(APIView):
    def post(self, request):
        key = request.data.get("token", "")
        tk = get_object_or_404(Token, key=key)
        return Response(UserSerializer(tk.user, many=False).data)

    def get(self, request):
        form = LoginForm(None)

        return render(request, "log_in.html", {"form": form, "msg": None})


class LogoutView(TemplateView):
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logout(request)
        return redirect("/")

    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            # Borrar el token del usuario
            Token.objects.filter(user=request.user).delete()
            logout(request)
        return JsonResponse({"status": "OK"})


class RegisterView(APIView):
    template_name = "registration_form.html"

    def handle_google_login(self, request):

        # Comprobar si es la primera vez que el usuario se logea con google
        social_account = SocialAccount.objects.filter(
            user=request.user, provider="google"
        ).first()
        if social_account is None:
            # Creamos un nuevo usuario django para esta cuenta de google
            social_account = SocialAccount.objects.create(
                user=request.user, provider="google"
            )
            social_account.save()
            return Response(
                {
                    "user_pk": social_account.user.pk,
                    "token": social_account.user.token.key,
                },
                status=HTTP_201_CREATED,
            )

        login(request, request.user)

        return Response(
            {
                "message": "Login successful",
                "user_pk": request.user.pk,
                "token": request.user.token.key,
            },
            status=HTTP_200_OK,
        )

    def post(self, request):
        # Verificar si el usuario que hace la solicitud es un superusuario o un usuario normal
        is_superuser = request.user.is_superuser

        # Si no es un superusuario, manejar el registro del usuario normal
        if not is_superuser:
            if request.POST.get("provider") == "google":
                return self.handle_google_login(request)

            form = UserCreationForm(request.data)
            if form.is_valid():
                user = form.save()
                token, _ = Token.objects.get_or_create(user=user)
                user_exists = User.objects.filter(username=user.username).exists()
                token_exists = Token.objects.filter(key=token.key).exists()
                if user_exists and token_exists:
                    return redirect("/")
            else:
                # Recuperar mensajes de error del formulario y agregarlos a los mensajes de Django
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field.capitalize()}: {error}")

                # Redirigir a la página de registro con los mensajes de error
                return redirect("register")

        # Si es un superusuario, manejar el registro del administrador
        if is_superuser:
            username = request.data.get("username", "")
            pwd = request.data.get("password", "")
            if not username or not pwd:
                return Response({}, status=HTTP_400_BAD_REQUEST)
            try:
                user, created = User.objects.get_or_create(username=username)
                if created:
                    user.set_password(pwd)
                    user.save()
                    token, _ = Token.objects.get_or_create(user=user)
                    return Response(
                        {"user_pk": user.pk, "token": token.key},
                        status=HTTP_201_CREATED,
                    )
                else:
                    return Response(
                        {"error": "User already exists"}, status=HTTP_400_BAD_REQUEST
                    )
            except IntegrityError:
                return Response({}, status=HTTP_400_BAD_REQUEST)

    def get(self, request):
        form = UserCreationForm()
        return render(request, "registration_form.html", {"form": form})
