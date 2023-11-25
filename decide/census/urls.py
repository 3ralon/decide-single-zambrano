from django.urls import path, include
from . import views


urlpatterns = [
    path('', views.CensusCreate.as_view(), name='census_create'),
    path('<int:voting_id>/', views.CensusDetail.as_view(), name='census_detail'),
    path('descargar-csv/', views.CensusExportationToCSV.export_page, name='export_page'),
    path('export-voting-to-csv/<int:voting_id>/', views.CensusExportationToCSV.export_voting_to_csv, name='export-voting-to-csv'),
    path('export-all-census/', views.CensusExportationToCSV.export_all_census, name='export-all-census'),
    path('export-to-csv/', views.CensusExportationToCSV.export_to_csv, name='export-to-csv'),

]