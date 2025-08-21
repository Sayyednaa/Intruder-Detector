from django.urls import path
from . import views
urlpatterns = [
    path('', views.monitor, name='monitor'),
    path('devices/', views.devices, name='devices'),
    path('devices/<int:pk>/', views.device_detail, name='device_detail'),
    path('events/', views.events, name='events'),
    path('client/', views.client_page, name='client'),
    path('pair/<int:pk>/', views.pair_qr, name='pair_qr'),
    path('api/upload_frame/', views.upload_frame, name='upload_frame'),
    path('api/last_frame/<str:token>.jpg', views.last_frame_jpg, name='last_frame_jpg'),
    
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('monitor/', views.monitor, name='monitor'),  # your dashboard
    
    # urls.py
    path('delete_all_data/', views.delete_all_data, name='delete_all_data'),
    path('device/delete/<int:pk>/', views.delete_device, name='delete_device'),

   
]
