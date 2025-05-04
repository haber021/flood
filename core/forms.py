from django import forms
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
