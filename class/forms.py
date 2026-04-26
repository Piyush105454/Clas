from django import forms
from django.contrib.auth.hashers import make_password
from .models import User, Role, School, Cluster, ClassSection,FacilitatorSchool

# Indian States
INDIAN_STATES = [
    ('Andhra Pradesh', 'Andhra Pradesh'),
    ('Arunachal Pradesh', 'Arunachal Pradesh'),
    ('Assam', 'Assam'),
    ('Bihar', 'Bihar'),
    ('Chhattisgarh', 'Chhattisgarh'),
    ('Goa', 'Goa'),
    ('Gujarat', 'Gujarat'),
    ('Haryana', 'Haryana'),
    ('Himachal Pradesh', 'Himachal Pradesh'),
    ('Jharkhand', 'Jharkhand'),
    ('Karnataka', 'Karnataka'),
    ('Kerala', 'Kerala'),
    ('Madhya Pradesh', 'Madhya Pradesh'),
    ('Maharashtra', 'Maharashtra'),
    ('Manipur', 'Manipur'),
    ('Meghalaya', 'Meghalaya'),
    ('Mizoram', 'Mizoram'),
    ('Nagaland', 'Nagaland'),
    ('Odisha', 'Odisha'),
    ('Punjab', 'Punjab'),
    ('Rajasthan', 'Rajasthan'),
    ('Sikkim', 'Sikkim'),
    ('Tamil Nadu', 'Tamil Nadu'),
    ('Telangana', 'Telangana'),
    ('Tripura', 'Tripura'),
    ('Uttar Pradesh', 'Uttar Pradesh'),
    ('Uttarakhand', 'Uttarakhand'),
    ('West Bengal', 'West Bengal'),
]

# ---------------- Add User Form ----------------
class AddUserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["full_name", "email", "password", "role"]
        widgets = {
            "full_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Full Name"
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "Email Address"
            }),
            "role": forms.Select(attrs={"class": "form-control"}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.password = make_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


# ---------------- Edit User Form ----------------
class EditUserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=False)

    class Meta:
        model = User
        fields = ["full_name", "email", "password", "role", "is_active"]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "role": forms.Select(attrs={"class": "form-control"}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.password = make_password(password)
        if commit:
            user.save()
        return user


# ---------------- Add School Form ----------------
class AddSchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ["name", "udise", "block", "district", "state", "cluster", "area", "address", "contact_person", "contact_number", "email", "latitude", "longitude", "logo", "status"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "School Name"}),
            "udise": forms.TextInput(attrs={"class": "form-control", "placeholder": "UDISE Code"}),
            "block": forms.TextInput(attrs={"class": "form-control", "placeholder": "Block"}),
            "district": forms.TextInput(attrs={"class": "form-control", "placeholder": "District"}),
            "state": forms.Select(attrs={"class": "form-control"}, choices=INDIAN_STATES),
            "cluster": forms.Select(attrs={"class": "form-control"}),
            "area": forms.TextInput(attrs={"class": "form-control", "placeholder": "Area"}),
            "address": forms.Textarea(attrs={"class": "form-control", "placeholder": "Address", "rows": 3}),
            "contact_person": forms.TextInput(attrs={"class": "form-control", "placeholder": "Contact Person"}),
            "contact_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "Contact Number"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email"}),
            "latitude": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Latitude", "step": "0.000001"}),
            "longitude": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Longitude", "step": "0.000001"}),
            "logo": forms.FileInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
        }


# ---------------- Edit School Form ----------------
class EditSchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = [
            "name", "udise", "block", "district", "state", "cluster", "area", "address", "contact_person", 
            "contact_number", "email", "latitude", "longitude", "status", "profile_image", "logo"
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "udise": forms.TextInput(attrs={"class": "form-control"}),
            "block": forms.TextInput(attrs={"class": "form-control"}),
            "district": forms.TextInput(attrs={"class": "form-control"}),
            "state": forms.Select(attrs={"class": "form-control"}, choices=INDIAN_STATES),
            "cluster": forms.Select(attrs={"class": "form-control"}),
            "area": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "contact_person": forms.TextInput(attrs={"class": "form-control"}),
            "contact_number": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "latitude": forms.NumberInput(attrs={"class": "form-control", "step": "0.000001"}),
            "longitude": forms.NumberInput(attrs={"class": "form-control", "step": "0.000001"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "profile_image": forms.FileInput(attrs={"class": "form-control"}),
            "logo": forms.FileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, (forms.TextInput, forms.NumberInput, forms.EmailInput)):
                field.widget.attrs["placeholder"] = field.label


# ---------------- Class Section Form ----------------
class ClassSectionForm(forms.ModelForm):
    CLASS_LEVEL_CHOICES = [
        ('LKG', 'LKG (Lower Kindergarten)'),
        ('UKG', 'UKG (Upper Kindergarten)'),
        ('1', 'Class 1'),
        ('2', 'Class 2'),
        ('3', 'Class 3'),
        ('4', 'Class 4'),
        ('5', 'Class 5'),
        ('6', 'Class 6'),
        ('7', 'Class 7'),
        ('8', 'Class 8'),
        ('9', 'Class 9'),
        ('10', 'Class 10'),
    ]
    
    SECTION_CHOICES = [
        ('A', 'Section A'),
        ('B', 'Section B'),
    ]
    
    school = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={
            "class": "form-control",
        }),
        label="School"
    )
    
    class_level = forms.ChoiceField(
        choices=CLASS_LEVEL_CHOICES,
        widget=forms.Select(attrs={
            "class": "form-control",
        })
    )
    
    section = forms.ChoiceField(
        choices=SECTION_CHOICES,
        initial='A',  # Default to Section A
        widget=forms.Select(attrs={
            "class": "form-control",
        })
    )
    
    academic_year = forms.CharField(
        initial="2024-2025",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g., 2024-2025"
        })
    )
    
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            "class": "form-check-input",
        }),
        label="Active"
    )

    class Meta:
        model = ClassSection
        fields = ["school", "class_level", "section", "academic_year", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set the school queryset to all active schools (status=1)
        from .models import School
        self.fields['school'].queryset = School.objects.filter(status=1).order_by('name')

    def clean_section(self):
        section = self.cleaned_data.get("section")
        if section:
            return section.strip().upper()
        return section

class AssignFacilitatorForm(forms.ModelForm):
    class Meta:
        model = FacilitatorSchool
        fields = ["facilitator", "school"]
        widgets = {
            "facilitator": forms.Select(attrs={
                "class": "form-control",
            }),
            "school": forms.Select(attrs={
                "class": "form-control",
            }),
        }

    def __init__(self, *args, **kwargs):
        facilitator_qs = kwargs.pop('facilitator_queryset', None)
        school_qs = kwargs.pop('school_queryset', None)
        super().__init__(*args, **kwargs)
        
        if facilitator_qs is not None:
            self.fields["facilitator"].queryset = facilitator_qs
        else:
            self.fields["facilitator"].queryset = User.objects.filter(
                role__name__iexact="FACILITATOR"
            )
            
        if school_qs is not None:
            self.fields["school"].queryset = school_qs
        else:
            from .models import School
            self.fields["school"].queryset = School.objects.filter(status=1).order_by('name')


# ---------------- Cluster Form ----------------
class ClusterForm(forms.ModelForm):
    class Meta:
        model = Cluster
        fields = ["name", "district", "state", "description", "latitude", "longitude"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Cluster Name"}),
            "district": forms.TextInput(attrs={"class": "form-control", "placeholder": "District"}),
            "state": forms.Select(attrs={"class": "form-control"}, choices=INDIAN_STATES),
            "description": forms.Textarea(attrs={"class": "form-control", "placeholder": "Description", "rows": 3}),
            "latitude": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Latitude", "step": "0.000001"}),
            "longitude": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Longitude", "step": "0.000001"}),
        }
