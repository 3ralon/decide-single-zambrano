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
        HTTP_409_CONFLICT as ST_409)
import csv
from django.views import View
from base.perms import UserIsStaff
from .models import Census
from django.http import HttpResponse
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
import csv
from .models import Census

class CensusExportationToCSV(View):     
    

    def get(self, request, *args, **kwargs):
        voting_id = kwargs.get('voting_id')
        if voting_id is not None:
            census = Census.objects.filter(voting_id=voting_id)
            filename = f"censo_{voting_id}.csv"
        else:
            census = Census.objects.all()
            filename = "CensoCompleto.csv"

        if not request.user.is_superuser:
            return HttpResponse("Only superusers can download census data")

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow(['Voting', 'Voter'])
        for profile in census:
            writer.writerow([profile.voting_id, profile.voter_id])

        return response


    def export_all_census(self, request):
            if not request.user.is_superuser:
                return HttpResponse("Only superusers can download census data")

            census = Census.objects.all()
            response = HttpResponse(
            content_type = 'text/csv',
            headers = {
                "Content-Disposition": 'attachment; filename="CensoCompleto.csv"'
                }
            )
            writer = csv.writer(response)
            writer.writerow(['Voting','Voter'])
            profile_fields = census.values_list('voting_id', 'voter_id')
            for profile in profile_fields:
                writer.writerow(profile)
            return response 

    def export_voting_to_csv(self, request, voting_id):
        if not request.user.is_superuser:
            return HttpResponse("Only superusers can download census data")

        census = Census.objects.filter(voting_id=voting_id)  
        response = HttpResponse(
        content_type='text/csv',
        headers={
            "Content-Disposition": 'attachment; filename="censo.csv"'
            } )
        writer = csv.writer(response)
        writer.writerow(['Voting', 'Voter'])
        for profile in census:
            writer.writerow([profile.voting_id, profile.voter_id])
        return response
    
    def export_to_csv(self, request):
        if not request.user.is_superuser:
            return HttpResponse("Only superusers can download census data")

        if request.method == 'GET':
            voting_id = request.GET.get('voting_id')
            if voting_id is not None:
                census = Census.objects.filter(voting_id=voting_id)
                response = HttpResponse(
                    content_type='text/csv',
                    headers={
                        "Content-Disposition": 'attachment; filename="censo.csv"'
                    }
                )
                writer = csv.writer(response)
                writer.writerow(['Voting', 'Voter'])
                for profile in census:
                    writer.writerow([profile.voting_id, profile.voter_id])
                return response
            else:
                return HttpResponse("No se proporcionó una ID de votación válida")
        else:
            return HttpResponse("Método de solicitud no válido")

    

   
    
class CensusCreate(generics.ListCreateAPIView):
    
    def create(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return Response('Only superusers can create censuses', status=status.HTTP_403_FORBIDDEN)

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
