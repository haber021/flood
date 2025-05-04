from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import FloodAlert, ThresholdSetting, Barangay

class FloodAlertForm(forms.ModelForm):
    """Form for creating and editing flood alerts"""
    class Meta:
        model = FloodAlert
        fields = ['title', 'description', 'severity_level', 'active', 'predicted_flood_time', 'affected_barangays']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'severity_level': forms.Select(attrs={'class': 'form-select'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'predicted_flood_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'affected_barangays': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
        }

class ThresholdSettingForm(forms.ModelForm):
    """Form for creating and editing threshold settings"""
    class Meta:
        model = ThresholdSetting
        fields = ['parameter', 'advisory_threshold', 'watch_threshold', 'warning_threshold', 'emergency_threshold', 'catastrophic_threshold', 'unit']
        widgets = {
            'parameter': forms.Select(attrs={'class': 'form-select'}),
            'advisory_threshold': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'watch_threshold': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'warning_threshold': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'emergency_threshold': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'catastrophic_threshold': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'unit': forms.TextInput(attrs={'class': 'form-control'}),
        }

class BarangaySearchForm(forms.Form):
    """Form for searching and filtering barangays"""
    name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search by name'})
    )
    
    severity_level = forms.ChoiceField(
        choices=[
            ('', 'All Severity Levels'),
            (1, 'Advisory'),
            (2, 'Watch'),
            (3, 'Warning'),
            (4, 'Emergency'),
            (5, 'Catastrophic'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class RegisterForm(UserCreationForm):
    """Registration form for new users"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        
    def __init__(self, *args, **kwargs):
        super(RegisterForm, self).__init__(*args, **kwargs)
        # Add Bootstrap classes to form fields
        self.fields['username'].widget.attrs['class'] = 'form-control'
        self.fields['username'].widget.attrs['placeholder'] = 'Choose a username'
        self.fields['password1'].widget.attrs['class'] = 'form-control'
        self.fields['password1'].widget.attrs['placeholder'] = 'Create a password'
        self.fields['password2'].widget.attrs['class'] = 'form-control'
        self.fields['password2'].widget.attrs['placeholder'] = 'Confirm your password'
        
    def save(self, commit=True):
        user = super(RegisterForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user
