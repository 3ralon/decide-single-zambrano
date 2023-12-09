from django import forms
from census.models import Census
from .models import Question, QuestionOption, Voting
from django.contrib.auth.models import User

class VotingForm(forms.ModelForm):
    class Meta:
        model = Voting
        fields = ['name', 'desc', 'question', 'auths']

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['desc', 'question_type']

class QuestionOptionForm(forms.ModelForm):
    class Meta:
        model = QuestionOption
        fields = ['option']

class CensusForm(forms.ModelForm):
    user = forms.ModelMultipleChoiceField(queryset=User.objects.all())
    class Meta:
        model = Census
        fields = ['user']

QuestionOptionFormSet = forms.modelformset_factory(QuestionOption, form=QuestionOptionForm, extra=5)