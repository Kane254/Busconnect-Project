

# Create your views here.
# booking_app/views.py

from .forms import UserRegisterForm
from django.contrib.auth import login
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import F
from django.db import transaction# F for atomic updates, transaction for atomicity
from django.utils import timezone

from .models import Trip, Booking, Stop, Payment
from .forms import TripSearchForm, BookingForm


def signup_view(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user) # Log the user in immediately after registration
            messages.success(request, f'Account created for {user.username}! You are now logged in.')
            return redirect('home') # Redirect to your homepage or a welcome page
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserRegisterForm()
    return render(request, 'registration/signup.html', {'form': form})

def home_view(request):
    search_form = TripSearchForm(request.GET or None)
    upcoming_trips = Trip.objects.filter(
        trip_date__gte=timezone.localdate(),
        available_seats__gt=0
    ).order_by('trip_date', 'departure_time')[:5]

    return render(request, 'booking_app/home.html', {
        'search_form': search_form,
        'upcoming_trips': upcoming_trips
    })

def trip_list_view(request):
    search_form = TripSearchForm(request.GET or None)
    trips = Trip.objects.none()

    if search_form.is_valid():
        departure_stop = search_form.cleaned_data['departure_stop']
        arrival_stop = search_form.cleaned_data['arrival_stop']
        trip_date = search_form.cleaned_data['trip_date']

        trips = Trip.objects.filter(
            route__departure_stop=departure_stop,
            route__arrival_stop=arrival_stop,
            trip_date=trip_date,
            available_seats__gt=0
        ).select_related('bus', 'route__departure_stop', 'route__arrival_stop')

        current_datetime = timezone.localtime(timezone.now())
        if trip_date == current_datetime.date():
            trips = trips.filter(departure_time__gte=current_datetime.time())

        if not trips.exists():
            messages.info(request, "No trips found matching your search criteria.")
    elif request.GET:
        messages.error(request, "Please correct the errors in your search.")

    return render(request, 'booking_app/trip_list.html', {
        'search_form': search_form,
        'trips': trips
    })

def trip_detail_view(request, pk):
    trip = get_object_or_404(Trip, pk=pk)

    current_datetime = timezone.localtime(timezone.now())
    if trip.trip_date < current_datetime.date() or \
       (trip.trip_date == current_datetime.date() and trip.departure_time < current_datetime.time()):
        messages.error(request, "This trip has already departed and cannot be booked.")
        return redirect('trip_list')

    booking_form = None
    if trip.available_seats > 0 and request.user.is_authenticated:
        booking_form = BookingForm(trip=trip)

    return render(request, 'booking_app/trip_detail.html', {
        'trip': trip,
        'booking_form': booking_form
    })

@login_required
def create_booking_and_initiate_payment(request, pk):
    """
    Creates a pending booking and redirects to the payment page.
    """
    trip = get_object_or_404(Trip, pk=pk)

    current_datetime = timezone.localtime(timezone.now())
    if trip.trip_date < current_datetime.date() or \
       (trip.trip_date == current_datetime.date() and trip.departure_time < current_datetime.time()):
        messages.error(request, "This trip has already departed and cannot be booked.")
        return redirect('trip_list')

    if request.method == 'POST':
        form = BookingForm(request.POST, trip=trip)
        if form.is_valid():
            num_seats = form.cleaned_data['num_seats']

            with transaction.atomic(): # Ensure atomicity for seat check and booking creation
                trip.refresh_from_db() # Get the latest data

                if num_seats > trip.available_seats:
                    messages.error(request, f"Sorry, only {trip.available_seats} seats left. Please try booking fewer seats.")
                    return redirect('trip_detail', pk=trip.pk)

                # Create booking with PENDING status (seats not yet decremented from Trip)
                booking = Booking.objects.create(
                    user=request.user,
                    trip=trip,
                    num_seats=num_seats,
                    total_price=num_seats * trip.route.price,
                    status='PENDING'
                )

                # Create a corresponding PENDING payment record
                Payment.objects.create(
                    booking=booking,
                    amount=booking.total_price,
                    status='PENDING'
                )

            messages.info(request, "Booking created. Please proceed to payment.")
            return redirect('initiate_payment', booking_id=booking.id)
        else:
            messages.error(request, "Please correct the errors below.")
            return render(request, 'booking_app/trip_detail.html', {'trip': trip, 'booking_form': form})
    else:
        return redirect('trip_detail', pk=pk)

@login_required
def initiate_payment_view(request, booking_id):
    """
    Displays payment details for a pending booking.
    """
    booking = get_object_or_404(Booking, id=booking_id, user=request.user, status='PENDING')
    payment = get_object_or_404(Payment, booking=booking, status='PENDING')

    return render(request, 'booking_app/initiate_payment.html', {
        'booking': booking,
        'payment': payment,
    })

@login_required
def process_dummy_payment(request, booking_id):
    """
    Simulates payment success/failure and updates booking/trip status.
    """
    if request.method == 'POST':
        booking = get_object_or_404(Booking, id=booking_id, user=request.user, status='PENDING')
        payment = get_object_or_404(Payment, booking=booking, status='PENDING')

        # --- SIMULATE PAYMENT LOGIC ---
        # In a real system, you'd integrate with a payment gateway here.
        # For simplicity, we'll always simulate success.
        payment_successful = True # Change to False to test failure

        if payment_successful:
            with transaction.atomic(): # Ensure atomicity for payment and seat update
                # Update Payment status
                payment.status = 'COMPLETED'
                payment.save()

                # Update Booking status
                booking.status = 'CONFIRMED'
                booking.save()

                # Decrease available seats on the trip
                trip = booking.trip
                trip.available_seats = F('available_seats') - booking.num_seats
                trip.save()
                trip.refresh_from_db() # Get the updated available_seats value

            messages.success(request, f"Payment successful! Your booking {booking.id} is confirmed.")
            return redirect('my_bookings')
        else:
            with transaction.atomic():
                # Update Payment status
                payment.status = 'FAILED'
                payment.save()

                # Update Booking status
                booking.status = 'FAILED_PAYMENT'
                booking.save()

            messages.error(request, "Payment failed. Please try again or contact support.")
            return redirect('initiate_payment', booking_id=booking.id) # Go back to payment page

    return redirect('home') # Redirect if accessed via GET

@login_required
def my_bookings_view(request):
    bookings = Booking.objects.filter(user=request.user).order_by('-booking_date')
    return render(request, 'booking_app/my_bookings.html', {'bookings': bookings})

# Optional: View to cancel a booking (and return seats)
@login_required
def cancel_booking_view(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if booking.status == 'CONFIRMED':
        # Return seats to the trip
        with transaction.atomic():
            booking.trip.available_seats = F('available_seats') + booking.num_seats
            booking.trip.save()
            booking.trip.refresh_from_db()

            booking.status = 'CANCELLED'
            booking.save()
            messages.success(request, f"Booking {booking.id} has been cancelled and seats returned.")
    else:
        # For pending or failed bookings, just mark as cancelled without seat return
        if booking.status != 'CANCELLED':
            booking.status = 'CANCELLED'
            booking.save()
            messages.info(request, f"Booking {booking.id} has been marked as cancelled.")

    return redirect('my_bookings')