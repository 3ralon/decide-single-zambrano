from django.urls import path, include
from . import views


urlpatterns = [
    path('', views.CensusCreate.as_view(), name='census_create'),
    path('<int:voting_id>/', views.CensusDetail.as_view(), name='census_detail'),
    path('descargar-csv/', views.CensusExportationToCSV.export_page, name='export_page'),
    path('export-to-csv/', views.CensusExportationToCSV.export_to_csv, name='export-to-csv')
]