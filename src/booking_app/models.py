# booking_app/models.py

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
import uuid # For unique transaction IDs

class Bus(models.Model):
    bus_number = models.CharField(max_length=50, unique=True)
    capacity = models.IntegerField(validators=[MinValueValidator(1)])

    def __str__(self):
        return f"Bus {self.bus_number} (Capacity: {self.capacity})"

class Stop(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Route(models.Model):
    departure_stop = models.ForeignKey(Stop, on_delete=models.CASCADE, related_name='departing_routes')
    arrival_stop = models.ForeignKey(Stop, on_delete=models.CASCADE, related_name='arriving_routes')
    price = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])

    def __str__(self):
        return f"{self.departure_stop.name} to {self.arrival_stop.name}"

    class Meta:
        unique_together = ('departure_stop', 'arrival_stop')

class Trip(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.PROTECT)
    route = models.ForeignKey(Route, on_delete=models.PROTECT)
    trip_date = models.DateField()
    departure_time = models.TimeField()
    available_seats = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    def save(self, *args, **kwargs):
        # When a new trip is created, set available seats to bus capacity
        # This will only be called on initial Trip creation, not on seat updates
        if not self.pk:
            self.available_seats = self.bus.capacity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.route} on {self.trip_date} at {self.departure_time}"

    class Meta:
        unique_together = ('bus', 'trip_date', 'departure_time')
        ordering = ['trip_date', 'departure_time']

class Booking(models.Model):
    BOOKING_STATUS_CHOICES = [
        ('PENDING', 'Pending Payment'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('FAILED_PAYMENT', 'Failed Payment'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    trip = models.ForeignKey(Trip, on_delete=models.PROTECT)
    num_seats = models.IntegerField(validators=[MinValueValidator(1)])
    booking_date = models.DateTimeField(auto_now_add=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=BOOKING_STATUS_CHOICES, default='PENDING')

    def save(self, *args, **kwargs):
        # Calculate total price before saving
        self.total_price = self.num_seats * self.trip.route.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Booking {self.id} ({self.status}) by {self.user.username} for {self.num_seats} seats on {self.trip}"

class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    transaction_id = models.CharField(max_length=100, unique=True, blank=True, null=True) # Dummy transaction ID

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = f"TXN-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Payment for Booking {self.booking.id} - Amount: {self.amount} - Status: {self.status}"
