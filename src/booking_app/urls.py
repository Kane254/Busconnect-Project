# booking_app/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('trips/', views.trip_list_view, name='trip_list'),
    path('trips/<int:pk>/', views.trip_detail_view, name='trip_detail'),
    path('trips/<int:pk>/create_booking/', views.create_booking_and_initiate_payment, name='create_booking'), # New endpoint
    path('payment/<int:booking_id>/initiate/', views.initiate_payment_view, name='initiate_payment'), # New endpoint
    path('payment/<int:booking_id>/process_dummy/', views.process_dummy_payment, name='process_dummy_payment'), # New endpoint
    path('my-bookings/', views.my_bookings_view, name='my_bookings'),
    path('my-bookings/<int:booking_id>/cancel/', views.cancel_booking_view, name='cancel_booking'), # New endpoint
    path('signup/', views.signup_view, name='signup'),
]