from django.http import HttpResponseRedirect
from django.urls import reverse
import django_filters.rest_framework
from django.conf import settings
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from rest_framework import generics, status
from rest_framework.response import Response
from django.views.generic import TemplateView
from rest_framework.permissions import IsAdminUser
from census.models import Census

from voting.forms import CensusForm, QuestionForm, QuestionOptionFormSet, VotingForm
from .models import Question, QuestionOption
from .serializers import SimpleVotingSerializer, VotingSerializer, QuestionSerializer
from base.perms import UserIsStaff
from base.models import Auth
from voting.models import Voting


class QuestionView(generics.ListCreateAPIView):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,)
    filterset_fields = ("id",)

    def post(self, request, *args, **kwargs):
        self.permission_classes = (UserIsStaff,)
        self.check_permissions(request)
        for data in ["desc", "question_type", "options"]:
            if data not in request.data:
                return Response({}, status=status.HTTP_400_BAD_REQUEST)

        question = Question(
            desc=request.data.get("desc"),
            question_type=request.data.get("question_type"),
        )
        question.save()
        if question.question_type == "YESNO":
            op1 = QuestionOption(question=question, option="Sí", number=1)
            op2 = QuestionOption(question=question, option="No", number=2)
            op1.save()
            op2.save()
        else:
            for idx, q_opt in enumerate(request.data.get("options")):
                opt = QuestionOption(question=question, option=q_opt, number=idx)
                opt.save()
        return Response({}, status=status.HTTP_201_CREATED)


class QuestionList(TemplateView):
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        if request.user.is_staff:
            questions = Question.objects.all()
            return render(request, "question_list.html", {"questions": questions})
        else:
            return render(request, '403.html', status=403)

class QuestionCreation(TemplateView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        if request.user.is_staff:
            form = QuestionForm()
            formset = QuestionOptionFormSet(
                prefix="options", queryset=QuestionOption.objects.none()
            )
            return render(
                request, "question_creation.html", {"form": form, "formset": formset}
            )
        else:
            return render(request, '403.html', status=403)

    def post(self, request):
        if request.user.is_staff:
            form = QuestionForm(request.POST)
            formset = QuestionOptionFormSet(request.POST, prefix="options")
            if form.is_valid() and formset.is_valid():
                question = form.save()
                if question.question_type == "YESNO":
                    op1 = QuestionOption(question=question, option="Sí", number=1)
                    op2 = QuestionOption(question=question, option="No", number=2)
                    op1.save()
                    op2.save()
                else:
                    options = formset.save(commit=False)
                    for option in options:
                        option.question = question
                        option.number = options.index(option) + 1
                        option.save()
                return redirect("question_list")
        else:
            return render(request, '403.html', status=403)

class QuestionDelete(TemplateView):

    permission_classes = [IsAdminUser]

    def post(self, request, question_id):
        if request.user.is_staff:
            question = get_object_or_404(Question, pk=question_id)
            question.delete()
            return redirect("question_list")
        else:
            return render(request, '403.html', status=403)


class VotingView(generics.ListCreateAPIView):
    queryset = Voting.objects.all()
    serializer_class = VotingSerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,)
    filterset_fields = ("id",)

    def get(self, request, *args, **kwargs):
        self.queryset = Voting.objects.all()
        version = request.version
        if version not in settings.ALLOWED_VERSIONS:
            version = settings.DEFAULT_VERSION
        if version == "v2":
            self.serializer_class = SimpleVotingSerializer

        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.permission_classes = (UserIsStaff,)
        self.check_permissions(request)
        for data in ["name", "desc", "question", "question_type", "question_opt"]:
            if data not in request.data:
                return Response({}, status=status.HTTP_400_BAD_REQUEST)

        question = Question(
            desc=request.data.get("question"),
            question_type=request.data.get("question_type"),
        )
        question.save()
        for idx, q_opt in enumerate(request.data.get("question_opt")):
            opt = QuestionOption(question=question, option=q_opt, number=idx)
            opt.save()
        voting = Voting(
            name=request.data.get("name"),
            desc=request.data.get("desc"),
            question=question,
        )
        voting.save()

        auth, _ = Auth.objects.get_or_create(
            url=settings.BASEURL, defaults={"me": True, "name": "test auth"}
        )
        auth.save()
        voting.auths.add(auth)
        return Response({}, status=status.HTTP_201_CREATED)


class VotingList(TemplateView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        if request.user.is_staff:
            votings = Voting.objects.all()
            return render(request, "voting_list.html", {"votings": votings})
        else:
            return render(request, '403.html', status=403)

    def start_voting(self, voting_id):
        if self.user.is_staff:
            voting = get_object_or_404(Voting, pk=voting_id)
            if voting.start_date:
                return HttpResponseRedirect(reverse("voting_list"))
            voting.create_pubkey()
            voting.start_date = timezone.now()
            voting.save()
            return redirect("voting_list")
        else:
            return Response({}, status=status.HTTP_403_FORBIDDEN)

    def stop_voting(self, voting_id):
        if self.user.is_staff:
            voting = get_object_or_404(Voting, pk=voting_id)
            if voting.end_date or not voting.start_date:
                return HttpResponseRedirect(reverse("voting_list"))
            voting.end_date = timezone.now()
            voting.save()
            return redirect("voting_list")
        else:
            return Response({}, status=status.HTTP_403_FORBIDDEN)


class VotingTally(TemplateView):
    permission_classes = [IsAdminUser]

    def get(self, request, voting_id, *args, **kwargs):
        if request.user.is_staff:
            voting = get_object_or_404(Voting, pk=voting_id)
            if voting.tally or not voting.end_date or not voting.start_date:
                return HttpResponseRedirect(reverse("voting_list"))
            token = request.session.get("auth-token", "")
            voting.tally_votes(token)
            return redirect("voting_list")
        else:
            return render(request, '403.html', status=403)

class VotingCreation(TemplateView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        if request.user.is_staff:
            form = VotingForm()
            return render(request, "voting_creation.html", {"form": form})
        else:
            return render(request, '403.html', status=403)

    def post(self, request):
        if self.request.user.is_staff:
            form = VotingForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect("voting_list")
            return render(request, "voting_creation.html", {"form": form})
        else:
            return render(request, '403.html', status=403)

class VotingDelete(TemplateView):
    permission_classes = [IsAdminUser]

    def post(self, request, voting_id):
        if request.user.is_staff:
            voting = get_object_or_404(Voting, pk=voting_id)
            voting.delete()
            return redirect("voting_list")
        else:
            return render(request, '403.html', status=403)

class CensusVoting(TemplateView):
    permission_classes = [IsAdminUser]

    def get(self, request, voting_id):
        if request.user.is_staff:
            form = CensusForm()
            return render(request, "census_voting.html", {"form": form})
        else:
            return render(request, '403.html', status=403)

    def post(self, request, voting_id):
        if self.request.user.is_staff:
            form = CensusForm(request.POST)
            if form.is_valid():
                users = form.cleaned_data["user"]
                for user in users:
                    if not Census.objects.filter(voting_id=voting_id, voter_id=user.id).exists():
                        census = Census(voting_id=voting_id, voter_id=user.id)
                        census.save()
                return redirect("voting_list")
            return render(request, "census_voting.html", {"form": form})
        else:
            return render(request, '403.html', status=403)


class VotingUpdate(generics.RetrieveUpdateDestroyAPIView):
    queryset = Voting.objects.all()
    serializer_class = VotingSerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,)
    permission_classes = (UserIsStaff,)

    def put(self, request, voting_id, *args, **kwars):
        action = request.data.get("action")
        if not action:
            return Response({}, status=status.HTTP_400_BAD_REQUEST)

        voting = get_object_or_404(Voting, pk=voting_id)
        msg = ""
        st = status.HTTP_200_OK
        if action == "start":
            if voting.start_date:
                msg = "Voting already started"
                st = status.HTTP_400_BAD_REQUEST
            else:
                voting.start_date = timezone.now()
                voting.save()
                msg = "Voting started"
        elif action == "stop":
            if not voting.start_date:
                msg = "Voting is not started"
                st = status.HTTP_400_BAD_REQUEST
            elif voting.end_date:
                msg = "Voting already stopped"
                st = status.HTTP_400_BAD_REQUEST
            else:
                voting.end_date = timezone.now()
                voting.save()
                msg = "Voting stopped"
        elif action == "tally":
            if not voting.start_date:
                msg = "Voting is not started"
                st = status.HTTP_400_BAD_REQUEST
            elif not voting.end_date:
                msg = "Voting is not stopped"
                st = status.HTTP_400_BAD_REQUEST
            elif voting.tally:
                msg = "Voting already tallied"
                st = status.HTTP_400_BAD_REQUEST
            else:
                voting.tally_votes(request.auth.key)
                msg = "Voting tallied"
        else:
            msg = "Action not found, try with start, stop or tally"
            st = status.HTTP_400_BAD_REQUEST
        return Response(msg, status=st)
