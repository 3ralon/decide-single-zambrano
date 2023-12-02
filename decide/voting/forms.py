from django import forms
from .models import Question, QuestionOption, Voting

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

QuestionOptionFormSet = forms.modelformset_factory(QuestionOption, form=QuestionOptionForm, extra=5)