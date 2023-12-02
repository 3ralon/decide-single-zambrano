from typing import Any
from django.db.utils import IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.status import (
        HTTP_200_OK as ST_200,
        HTTP_201_CREATED as ST_201,
        HTTP_204_NO_CONTENT as ST_204,
        HTTP_400_BAD_REQUEST as ST_400,
        HTTP_401_UNAUTHORIZED as ST_401,
        HTTP_403_FORBIDDEN as ST_403,
        HTTP_409_CONFLICT as ST_409)
import csv
from django.views import View
from base.perms import UserIsStaff
from .models import Census
from django.http import HttpResponse, HttpResponseForbidden
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
import csv
from .models import Census
from voting.models import Voting
from django.views.generic.base import TemplateView


class CensusExportationToCSV(TemplateView):
    template_name = "export_csv.html"

    def get_context_data(self, **kwargs: Any):
        votaciones = Voting.objects.all().count()
        context = super().get_context_data(**kwargs)
        context['votaciones'] = votaciones
        return context

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated == None or request.user.is_authenticated is False:
            return HttpResponseForbidden('Debes estar logueado para poder descargar el csv')
        elif not request.user.is_superuser:
            return HttpResponseForbidden('Solo los superuser pueden descargar los datos del censo')
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return HttpResponseForbidden('Solo los superuser pueden descargar los datos del censo')
        voting_id = request.POST.get('voting_id') or kwargs.get('voting_id')
        filename = f"Censo_{voting_id}.csv" if voting_id else "CensoCompleto.csv"
        census = Census.objects.filter(voting_id=voting_id) if voting_id else Census.objects.all()
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        writer = csv.writer(response)
        writer.writerow(['Voting', 'Voter'])
        for profile in census:
            writer.writerow([profile.voting_id, profile.voter_id])
        return response
    


class CensusCreate(generics.ListCreateAPIView):
    
    permission_classes = (UserIsStaff,)
    
    def create(self, request, *args, **kwargs):
        voting_id = request.data.get('voting_id')
        voters = request.data.get('voters')
        try:
            for voter in voters:
                census = Census(voting_id=voting_id, voter_id=voter)
                census.save()
        except IntegrityError:
            return Response('Error try to create census', status=ST_409)
        return Response('Census created', status=ST_201)

    def list(self, request, *args, **kwargs):
        voting_id = request.GET.get('voting_id')
        voters = Census.objects.filter(voting_id=voting_id).values_list('voter_id', flat=True)
        return Response({'voters': voters})


class CensusDetail(generics.RetrieveDestroyAPIView):

    def destroy(self, request, voting_id, *args, **kwargs):
        voters = request.data.get('voters')
        census = Census.objects.filter(voting_id=voting_id, voter_id__in=voters)
        census.delete()
        return Response('Voters deleted from census', status=ST_204)

    def retrieve(self, request, voting_id, *args, **kwargs):
        voter = request.GET.get('voter_id')
        try:
            Census.objects.get(voting_id=voting_id, voter_id=voter)
        except ObjectDoesNotExist:
            return Response('Invalid voter', status=ST_401)
        return Response('Valid voter')
