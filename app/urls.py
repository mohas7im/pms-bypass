from django.urls import path
from . import views

urlpatterns = [
    path('', views.index_view, name='index'),
    path('api/test-connection/', views.test_connection_view, name='test_connection'),
    path('api/project-details/', views.project_details_view, name='project_details'),
    path('api/upload-preview/', views.upload_preview_view, name='upload_preview'),
    path('api/execute-import/', views.execute_import_view, name='execute_import'),
    path('api/disconnect/', views.disconnect_view, name='disconnect'),
    path('download-sample/<str:format_type>/', views.download_sample_view, name='download_sample'),
]
