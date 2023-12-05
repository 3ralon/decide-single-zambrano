from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.CensusCreate.as_view(), name='census_create'),
    path('<int:voting_id>/', views.CensusDetail.as_view(), name='census_detail'),
    path('descargar-csv/', views.CensusExportationToCSV.as_view(), name='export_page'),
    path('export-voting-to-csv/<int:voting_id>/', views.CensusExportationToCSV.as_view(), name='export-voting-to-csv'),
    path('export-all-census/', views.CensusExportationToCSV.as_view(), name='export-all-census'),
    path('export-to-csv/', views.CensusExportationToCSV.as_view(), name='export-to-csv'),
]