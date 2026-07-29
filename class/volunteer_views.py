from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Volunteer
from .volunteer_forms import VolunteerForm

@login_required
def admin_volunteers_list(request):
    if request.user.role.name.upper() != "ADMIN":
        messages.error(request, "You do not have permission to view this page.")
        return redirect("no_permission")

    volunteers_queryset = Volunteer.objects.all().order_by('-created_at')

    # Extract unique values for filter dropdowns (before applying filters)
    unique_cities = Volunteer.objects.exclude(city='').values_list('city', flat=True).distinct().order_by('city')
    unique_countries = Volunteer.objects.exclude(country='').values_list('country', flat=True).distinct().order_by('country')
    unique_orgs = Volunteer.objects.exclude(organization_name='').values_list('organization_name', flat=True).distinct().order_by('organization_name')

    # Apply search filter
    search_query = request.GET.get('search', '').strip()
    if search_query:
        volunteers_queryset = volunteers_queryset.filter(
            Q(full_name__icontains=search_query) |
            Q(personal_email__icontains=search_query) |
            Q(work_email__icontains=search_query) |
            Q(phone_number__icontains=search_query) |
            Q(organization_name__icontains=search_query)
        )

    # Apply dropdown filters
    city_filter = request.GET.get('city', '').strip()
    if city_filter:
        volunteers_queryset = volunteers_queryset.filter(city__iexact=city_filter)

    frequency_filter = request.GET.get('frequency', '').strip()
    if frequency_filter:
        try:
            volunteers_queryset = volunteers_queryset.filter(frequency_per_month=int(frequency_filter))
        except ValueError:
            pass

    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        volunteers_queryset = volunteers_queryset.filter(status=status_filter)

    role_filter = request.GET.get('role', '').strip()
    if role_filter:
        volunteers_queryset = volunteers_queryset.filter(role_type=role_filter)

    type_filter = request.GET.get('type', '').strip()
    if type_filter:
        volunteers_queryset = volunteers_queryset.filter(organization_type=type_filter)

    org_filter = request.GET.get('organization', '').strip()
    if org_filter:
        volunteers_queryset = volunteers_queryset.filter(organization_name__iexact=org_filter)

    country_filter = request.GET.get('country', '').strip()
    if country_filter:
        volunteers_queryset = volunteers_queryset.filter(country__iexact=country_filter)

    # Pre-calculate counts for stat cards (on the entire unfiltered set or filtered set? Let's do entire set for global stats)
    total_count = Volunteer.objects.count()
    active_count = Volunteer.objects.filter(status='ACTIVE').count()
    inactive_count = Volunteer.objects.filter(status='INACTIVE').count()
    regular_count = Volunteer.objects.filter(regular_volunteering=True).count()

    # Pagination: 20 volunteers per page
    paginator = Paginator(volunteers_queryset, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, "admin/volunteers/list.html", {
        "volunteers": page_obj.object_list,
        "page_obj": page_obj,
        "total_count": total_count,
        "active_count": active_count,
        "inactive_count": inactive_count,
        "regular_count": regular_count,
        # Unique filters list
        "unique_cities": unique_cities,
        "unique_countries": unique_countries,
        "unique_orgs": unique_orgs,
        # Selected filter values to persist on reload
        "search_query": search_query,
        "selected_city": city_filter,
        "selected_frequency": frequency_filter,
        "selected_status": status_filter,
        "selected_role": role_filter,
        "selected_type": type_filter,
        "selected_org": org_filter,
        "selected_country": country_filter,
    })

@login_required
def admin_volunteer_add(request):
    if request.user.role.name.upper() != "ADMIN":
        messages.error(request, "You do not have permission to perform this action.")
        return redirect("no_permission")

    if request.method == "POST":
        form = VolunteerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Volunteer added successfully!")
            return redirect("admin_volunteers")
        else:
            messages.error(request, "Error adding volunteer. Please check the form fields.")
    else:
        form = VolunteerForm()

    return render(request, "admin/volunteers/add.html", {"form": form})

@login_required
def admin_volunteer_edit(request, volunteer_id):
    if request.user.role.name.upper() != "ADMIN":
        messages.error(request, "You do not have permission to perform this action.")
        return redirect("no_permission")

    volunteer = get_object_or_404(Volunteer, id=volunteer_id)

    if request.method == "POST":
        form = VolunteerForm(request.POST, instance=volunteer)
        if form.is_valid():
            form.save()
            messages.success(request, "Volunteer updated successfully!")
            return redirect("admin_volunteers")
        else:
            messages.error(request, "Error updating volunteer. Please check the form fields.")
    else:
        form = VolunteerForm(instance=volunteer)

    return render(request, "admin/volunteers/edit.html", {
        "form": form,
        "volunteer": volunteer
    })

@login_required
def admin_volunteer_delete(request, volunteer_id):
    if request.user.role.name.upper() != "ADMIN":
        messages.error(request, "You do not have permission to perform this action.")
        return redirect("no_permission")

    volunteer = get_object_or_404(Volunteer, id=volunteer_id)
    try:
        volunteer.delete()
        messages.success(request, "Volunteer deleted successfully!")
    except Exception as e:
        messages.error(request, f"Failed to delete volunteer: {str(e)}")

    return redirect("admin_volunteers")
