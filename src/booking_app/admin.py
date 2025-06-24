

# Register your models here.
# booking_app/admin.py

from django.contrib import admin
from .models import Bus, Stop, Route, Trip, Booking, Payment

admin.site.register(Bus)
admin.site.register(Stop)
admin.site.register(Route)
admin.site.register(Payment) # Register the new Payment model

@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('route', 'bus', 'trip_date', 'departure_time', 'available_seats', 'price_display')
    list_filter = ('trip_date', 'route__departure_stop', 'route__arrival_stop', 'bus__capacity')
    search_fields = ('route__departure_stop__name', 'route__arrival_stop__name', 'bus__bus_number')
    ordering = ('trip_date', 'departure_time')

    def price_display(self, obj):
        return obj.route.price
    price_display.short_description = 'Price'

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'trip', 'num_seats', 'total_price', 'status', 'booking_date')
    list_filter = ('status', 'booking_date', 'trip__route__departure_stop', 'trip__route__arrival_stop')
    search_fields = ('user__username', 'trip__route__departure_stop__name', 'status')
    readonly_fields = ('booking_date', 'total_price') # These are auto-calculated