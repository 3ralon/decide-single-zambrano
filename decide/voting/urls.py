from django.urls import path
from . import views


urlpatterns = [
    path('', views.VotingView.as_view(), name='voting'),
    path('<int:voting_id>/', views.VotingUpdate.as_view(), name='voting'),
    path('question/', views.QuestionView.as_view(), name='question'),
    path('list/', views.VotingList.as_view(), name='voting_list'),
    path('add/', views.VotingCreation.as_view(), name='voting_creation'),
    path('stop/<int:voting_id>/', views.VotingList.stop_voting, name='voting_stop'),
    path('question/list/', views.QuestionList.as_view(), name='question_list'),
    path('question/add/', views.QuestionCreation.as_view(), name='question_creation'),
]
