from django.urls import path
from . import views


urlpatterns = [
    path('', views.VotingView.as_view(), name='voting'),
    path('<int:voting_id>/', views.VotingUpdate.as_view(), name='voting'),
    path('question/', views.QuestionView.as_view(), name='question'),
    path('list/', views.VotingList.as_view(), name='voting_list'),
    path('add/', views.VotingCreation.as_view(), name='voting_creation'),
    path('delete/<int:voting_id>/', views.VotingDelete.as_view(), name='voting_delete'),
    path('census/<int:voting_id>/', views.CensusVoting.as_view(), name='census_voting'),
    path('start/<int:voting_id>/', views.VotingList.start_voting, name='voting_start'),
    path('stop/<int:voting_id>/', views.VotingList.stop_voting, name='voting_stop'),
    path('tally/<int:voting_id>/', views.VotingTally.as_view(), name='voting_tally'),
    path('question/list/', views.QuestionList.as_view(), name='question_list'),
    path('question/add/', views.QuestionCreation.as_view(), name='question_creation'),
    path('question/delete/<int:question_id>/', views.QuestionDelete.as_view(), name='question_delete'),
]
