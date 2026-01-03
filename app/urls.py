from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),

    path("login/", LoginView.as_view(template_name="app/login.html"), name="login"),
    path('logout/', LogoutView.as_view(), name='logout'),

    path('info_today/', views.info_today, name='info_today'),  
    path('info/<str:work_date>/', views.info, name='info'),    
    path('info_dispatch/<str:work_date>/', views.info_dispatch, name='info_dispatch'),
    
    path('place_remarks/<int:place_id>/<str:work_date>/edit', views.place_remarks_edit, name='place_remarks_edit'),  
    path('place_remarks/<int:place_id>/<str:work_date>/save', views.place_remarks_save, name='place_remarks_save'),  

    path('staff/', views.staff_list, name='staff_list'),
    path('staff/dispatch/', views.staff_list_dispatch, name='staff_list_dispatch'),
    path('staff/create/', views.staff_create, name='staff_create'),
    path('staff/<int:staff_id>/edit/', views.staff_edit, name='staff_edit'),
    path('staff/<int:staff_id>/save/', views.staff_save, name='staff_save'),    
    path('staff/<int:staff_id>/<str:work_date>/edit', views.staff_record_edit, name='staff_record_edit'),
    path('staff/<int:staff_id>/<str:work_date>/save', views.staff_record_save, name='staff_record_save'),

    path('customer/', views.customer_list, name='customer_list'),
    path('customer/dispatch/', views.customer_list_dispatch, name='customer_list_dispatch'),
    path('customer/create/', views.customer_create, name='customer_create'),
    path('customer/<int:customer_id>/edit/', views.customer_edit, name='customer_edit'),
    path('customer/<int:customer_id>/save/', views.customer_save, name='customer_save'),     
    path('customer/<int:customer_id>/<str:work_date>/edit', views.customer_record_edit, name='customer_record_edit'),
    path('customer/<int:customer_id>/<str:work_date>/save', views.customer_record_save, name='customer_record_save'),

    path('output/', views.output, name='output'),      
    path('output/execute', views.output_execute, name='output_execute'),  
    path('sysad/', views.sysad, name='sysad'), 
    path('sysad/delete_record', views.delete_record, name='delete_record'), 
      

    path('password_change/', views.password_change, name='password_change'),  
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='app/password_change_done.html'), name='password_change_done'),  
]