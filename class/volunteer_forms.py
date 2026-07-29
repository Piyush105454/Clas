from django import forms
from .models import Volunteer

class VolunteerForm(forms.ModelForm):
    class Meta:
        model = Volunteer
        fields = [
            'full_name', 'role_type', 'organization_type', 'organization_name',
            'personal_email', 'work_email', 'country', 'city', 'phone_number',
            'linkedin_profile', 'regular_volunteering', 'frequency_per_month',
            'interested_area', 'interested_topic', 'preferred_day', 'preferred_class',
            'status'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Full Name'
            }),
            'role_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            }),
            'organization_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            }),
            'organization_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'e.g. Microsoft'
            }),
            'personal_email': forms.EmailField().widget, # We can override below or let Django default to EmailInput
            'personal_email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Personal Email'
            }),
            'work_email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Work Email'
            }),
            'country': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'value': 'India'
            }),
            'city': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'value': 'Bangalore'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Phone Number'
            }),
            'linkedin_profile': forms.URLInput(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'https://www.linkedin.com/in/...'
            }),
            'regular_volunteering': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-2 focus:ring-blue-500'
            }),
            'frequency_per_month': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'min': '0',
                'value': '0'
            }),
            'interested_area': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'e.g. Technology'
            }),
            'interested_topic': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'e.g. Artificial Intelligence'
            }),
            'preferred_day': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            }),
            'preferred_class': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'e.g. Class 10'
            }),
            'status': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Fetch distinct class levels from ClassSection
        from .models import ClassSection
        class_levels = ClassSection.objects.values_list('class_level', flat=True).distinct().order_by('class_level')
        
        # Sort using CLASS_LEVEL_ORDER helper
        order_map = ClassSection.CLASS_LEVEL_ORDER
        sorted_levels = sorted(class_levels, key=lambda c: order_map.get(c, 999))
        
        # Build choices
        choices = [('', 'None')] + [(level, f"Class {level}" if level.isdigit() else level) for level in sorted_levels]
        
        self.fields['preferred_class'] = forms.ChoiceField(
            choices=choices,
            required=False,
            widget=forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            })
        )

    def clean(self):
        cleaned_data = super().clean()
        personal_email = cleaned_data.get('personal_email')
        work_email = cleaned_data.get('work_email')

        if not personal_email and not work_email:
            raise forms.ValidationError("At least one email (personal or work) is required.")

        return cleaned_data
