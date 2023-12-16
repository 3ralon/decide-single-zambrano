from django.urls import path
from .views import BoothView
from . import views


urlpatterns = [
    path("vote/<int:voting_id>/", BoothView.as_view(), name="booth_vote"),
    path("", views.index, name="home"),
]
