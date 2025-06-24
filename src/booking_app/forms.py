# booking_app/forms.py

from django import forms
from .models import Booking, Stop
from django.utils import timezone
from datetime import date

# booking_app/forms.py (Add this new import and form class)

from django.contrib.auth.forms import UserCreationForm # Import Django's built-in user creation form

# ... (your existing forms like TripSearchForm, BookingForm) ...

class UserRegisterForm(UserCreationForm):
    # If you want to add more fields later, you can define them here.
    # For now, we'll just use the default UserCreationForm fields (username, password, password confirmation).
    class Meta(UserCreationForm.Meta):
        fields = UserCreationForm.Meta.fields + ('email',) # Optionally add email
        # You can customize labels or widgets if needed

class TripSearchForm(forms.Form):
    departure_stop = forms.ModelChoiceField(
        queryset=Stop.objects.all(),
        empty_label="Select Departure Stop",
        label="From",
        required=True
    )
    arrival_stop = forms.ModelChoiceField(
        queryset=Stop.objects.all(),
        empty_label="Select Arrival Stop",
        label="To",
        required=True
    )
    trip_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text="YYYY-MM-DD",
        required=True,
        label="Date"
    )

    def clean(self):
        cleaned_data = super().clean()
        departure_stop = cleaned_data.get('departure_stop')
        arrival_stop = cleaned_data.get('arrival_stop')
        trip_date = cleaned_data.get('trip_date')

        if departure_stop and arrival_stop and departure_stop == arrival_stop:
            self.add_error('arrival_stop', "Departure and arrival stops cannot be the same.")

        if trip_date and trip_date < timezone.localdate():
            self.add_error('trip_date', "Trip date cannot be in the past.")

        return cleaned_data

class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['num_seats']
        widgets = {
            'num_seats': forms.NumberInput(attrs={'min': 1})
        }

    def __init__(self, *args, **kwargs):
        self.trip = kwargs.pop('trip', None)
        super().__init__(*args, **kwargs)
        if self.trip:
            # We display current available seats, but the actual seat reduction happens after payment
            self.fields['num_seats'].widget.attrs['max'] = self.trip.available_seats
            self.fields['num_seats'].help_text = f"Maximum {self.trip.available_seats} seats currently showing as available."

    def clean_num_seats(self):
        num_seats = self.cleaned_data.get('num_seats')
        if not self.trip:
            raise forms.ValidationError("Trip information is missing for booking.")

        if num_seats is None:
            raise forms.ValidationError("Please enter the number of seats.")

        if num_seats <= 0:
            raise forms.ValidationError("Number of seats must be at least 1.")

        # This check is still valid for initial form submission, but the final check
        # and seat reduction happens at payment confirmation.
        if num_seats > self.trip.available_seats:
            raise forms.ValidationError(f"Only {self.trip.available_seats} seats available for this trip.")
        return num_seats