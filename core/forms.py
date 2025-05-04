from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group
from .models import FloodAlert, ThresholdSetting, Barangay, Municipality, UserProfile

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
    
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'})
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'})
    )
    
    role = forms.ChoiceField(
        choices=[
            ('viewer', 'Data Viewer - Can only view data'),
            ('officer', 'Municipal Officer - Can view data and create alerts'),
            ('operator', 'System Operator - Can manage sensors and view data'),
            ('manager', 'Flood Manager - Can manage alerts and sensors'),
        ],
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    municipality = forms.ModelChoiceField(
        queryset=Municipality.objects.filter(is_active=True),
        required=False,
        empty_label="Select municipality (optional)",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number (optional)'})
    )
    
    receive_alerts = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    receive_sms = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    receive_email = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
        
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
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            
            # Create or update the user profile
            if hasattr(user, 'profile'):
                profile = user.profile
            else:
                profile = UserProfile(user=user)
                
            # Update profile fields
            profile.role = self.cleaned_data['role']
            profile.municipality = self.cleaned_data.get('municipality')
            profile.phone_number = self.cleaned_data.get('phone_number')
            profile.receive_alerts = self.cleaned_data.get('receive_alerts', True)
            profile.receive_sms = self.cleaned_data.get('receive_sms', False)
            profile.receive_email = self.cleaned_data.get('receive_email', True)
            profile.save()
            
            # Add user to appropriate group
            if self.cleaned_data['role'] == 'manager':
                group = Group.objects.get(name='Flood Managers')
            elif self.cleaned_data['role'] == 'officer':
                group = Group.objects.get(name='Municipal Officers')
            elif self.cleaned_data['role'] == 'operator':
                group = Group.objects.get(name='System Operators')
            else:  # default to viewer
                group = Group.objects.get(name='Viewers')
                
            user.groups.clear()
            user.groups.add(group)
            
        return user


class UserProfileForm(forms.ModelForm):
    """Form for editing user profiles"""
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = UserProfile
        fields = ['role', 'municipality', 'barangay', 'phone_number', 
                 'receive_alerts', 'receive_sms', 'receive_email']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'municipality': forms.Select(attrs={'class': 'form-select'}),
            'barangay': forms.Select(attrs={'class': 'form-select'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'receive_alerts': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'receive_sms': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'receive_email': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
    def __init__(self, *args, **kwargs):
        # Get the user instance to populate initial values
        user = kwargs.pop('user', None)
        super(UserProfileForm, self).__init__(*args, **kwargs)
        
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email
            
    def save(self, user=None, commit=True):
        profile = super(UserProfileForm, self).save(commit=False)
        
        if user:
            # Update the User model fields
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.email = self.cleaned_data['email']
            
            if commit:
                user.save()
                
                # Update user's group based on role
                user.groups.clear()
                
                if profile.role == 'admin':
                    group = Group.objects.get(name='Administrators')
                elif profile.role == 'manager':
                    group = Group.objects.get(name='Flood Managers')
                elif profile.role == 'officer':
                    group = Group.objects.get(name='Municipal Officers')
                elif profile.role == 'operator':
                    group = Group.objects.get(name='System Operators')
                else:  # default to viewer
                    group = Group.objects.get(name='Viewers')
                    
                user.groups.add(group)
        
        if commit:
            profile.save()
            
        return profile
