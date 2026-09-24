"""
Views for OYA accounts.
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from core.exceptions import ValidationError, DuplicateRecordError
from core.utils import exclude_removed_users, exclude_admin_users
from auditlogs.services import log_request_action
from .models import User
from .forms import (
    LoginForm, UserCreateForm, UserUpdateForm,
    FloorMemberProfileForm, PINResetForm, ChangePINForm
)
from .permissions import AdminRequiredMixin, ExecutiveRequiredMixin

logger = logging.getLogger("oya")


def login_view(request):
    """Handle user login with serial number and PIN."""
    if request.user.is_authenticated:
        return redirect("dashboard:index")

    form = LoginForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            serial_number = form.cleaned_data.get("serial_number")
            pin = form.cleaned_data.get("pin")
            user = authenticate(
                request,
                serial_number=serial_number,
                pin=pin
            )
            if user is not None:
                login(request, user)
                log_request_action(
                    request,
                    action="LOGIN",
                    object_type="User",
                    object_id=user.id,
                    description=f"User {user.serial_number} logged in"
                )
                messages.success(request, f"Welcome, {user.full_name}!")
                return redirect("dashboard:index")
            else:
                # Distinguish between bad credentials vs inactive account
                # We do a second lookup to check if the account exists but is inactive
                try:
                    inactive_user = User.objects.get(serial_number=serial_number.upper().strip())
                    if not inactive_user.is_active:
                        form.add_error(None, "This account has been deactivated. Contact an administrator.")
                    else:
                        form.add_error(None, "Invalid serial number or PIN. Please check your credentials and try again.")
                except User.DoesNotExist:
                    form.add_error(None, "Invalid serial number or PIN. Please check your credentials and try again.")

    return render(request, "accounts/login.html", {"form": form})

def logout_view(request):
    """Handle user logout."""
    if request.user.is_authenticated:
        log_request_action(
            request,
            action="LOGOUT",
            object_type="User",
            object_id=request.user.id,
            description=f"User {request.user.serial_number} logged out"
        )
        logout(request)
        messages.success(request, "You have been logged out.")
    return redirect("accounts:login")


@login_required
def user_list(request):
    """List all users with search and pagination."""
    queryset = User.objects.all()
    search_term = request.GET.get("search", "")

    if search_term:
        queryset = queryset.filter(
            Q(serial_number__icontains=search_term) |
            Q(full_name__icontains=search_term) |
            Q(phone__icontains=search_term) |
            Q(state__icontains=search_term) |
            Q(role__icontains=search_term)
        )

    role_filter = request.GET.get("role", "")
    if role_filter:
        queryset = queryset.filter(role=role_filter)

    paginator = Paginator(queryset, 25)
    page = request.GET.get("page", 1)
    users = paginator.get_page(page)

    context = {
        "users": users,
        "search_term": search_term,
        "role_filter": role_filter,
        "role_choices": User.ROLE_CHOICES,
    }
    return render(request, "accounts/user_list.html", context)


@login_required
def user_detail(request, pk):
    """Display user details."""
    user = get_object_or_404(User, pk=pk)
    return render(request, "accounts/user_detail.html", {"user_obj": user})


@login_required
def user_create(request):
    """Create a new user (admin and executive)."""
    if not request.user.has_executive_access():
        messages.error(request, "You do not have permission to create users.")
        return redirect("accounts:user_list")

    if request.method == "POST":
        form = UserCreateForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            # Enforce admin defaults for newly created users
            user.role = "ADMIN"
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.save()
            log_request_action(
                request,
                action="CREATE",
                object_type="User",
                object_id=user.id,
                description=f"Created user {user.serial_number}"
            )
            messages.success(request, f"User {user.serial_number} created successfully.")
            return redirect("accounts:user_list")
        else:
            for error_list in form.errors.values():
                for error in error_list:
                    messages.error(request, error)
    else:
        form = UserCreateForm()

    return render(request, "accounts/user_form.html", {
        "form": form,
        "title": "Create User",
        "action": "Create"
    })


@login_required
def user_update(request, pk):
    """Update an existing user."""
    user = get_object_or_404(User, pk=pk)

    if request.user.is_floor_member() and request.user.id != user.id:
        messages.error(request, "You can only edit your own profile.")
        return redirect("dashboard:index")

    if request.user.is_floor_member():
        if request.method == "POST":
            form = FloorMemberProfileForm(request.POST, request.FILES, instance=user)
            if form.is_valid():
                form.save()
                log_request_action(
                    request,
                    action="UPDATE",
                    object_type="User",
                    object_id=user.id,
                    description=f"Updated profile for {user.serial_number}"
                )
                messages.success(request, "Profile updated successfully.")
                return redirect("accounts:profile")
        else:
            form = FloorMemberProfileForm(instance=user)
        return render(request, "accounts/profile_edit.html", {"form": form})

    if request.method == "POST":
        form = UserUpdateForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            pin_changed = bool(form.cleaned_data.get("new_pin"))
            user = form.save()

            if pin_changed and request.user.id == user.id:
                update_session_auth_hash(request, user)

            log_request_action(
                request,
                action="UPDATE",
                object_type="User",
                object_id=user.id,
                description=f"Updated user {user.serial_number}"
            )
            messages.success(request, f"User {user.serial_number} updated successfully.")
            return redirect("accounts:user_list")
        else:
            for error_list in form.errors.values():
                for error in error_list:
                    messages.error(request, error)
    else:
        form = UserUpdateForm(instance=user)

    return render(request, "accounts/user_form.html", {
        "form": form,
        "title": "Update User",
        "action": "Update",
        "user_obj": user
    })


@login_required
def user_delete(request, pk):
    """Delete a user (admin only)."""
    if not request.user.has_admin_access():
        messages.error(request, "Admin access required.")
        return redirect("accounts:user_list")

    user = get_object_or_404(User, pk=pk)

    if request.method == "POST":
        serial = user.serial_number
        user.delete()
        log_request_action(
            request,
            action="DELETE",
            object_type="User",
            object_id=pk,
            description=f"Deleted user {serial}"
        )
        messages.success(request, f"User {serial} deleted successfully.")
        return redirect("accounts:user_list")

    return render(request, "accounts/user_confirm_delete.html", {"user_obj": user})


@login_required
def pin_reset(request):
    """Reset a user's PIN (admin only)."""
    if not request.user.has_admin_access():
        messages.error(request, "Admin access required to reset PINs.")
        return redirect("dashboard:index")

    if request.method == "POST":
        form = PINResetForm(request.POST)
        if form.is_valid():
            serial_number = form.cleaned_data["serial_number"]
            new_pin = form.cleaned_data["new_pin"]

            try:
                user = User.objects.get(serial_number=serial_number)
                user.set_pin(new_pin)
                user.save()

                log_request_action(
                    request,
                    action="PIN_RESET",
                    object_type="User",
                    object_id=user.id,
                    description=f"PIN reset for user {user.serial_number}"
                )
                messages.success(
                    request,
                    f"PIN for {user.serial_number} has been reset successfully."
                )
                return redirect("accounts:user_list")
            except User.DoesNotExist:
                messages.error(request, "User not found.")
        else:
            for error_list in form.errors.values():
                for error in error_list:
                    messages.error(request, error)
    else:
        form = PINResetForm()

    return render(request, "accounts/pin_reset.html", {"form": form})


@login_required
def profile_view(request):
    """View own profile with dues, donations, and full contribution tracking."""
    from finance.models import Income, Expense, DuesPayment, DuesPaymentTransaction
    from notifications.models import Notification
    from django.conf import settings
    from django.db.models import Sum, Value, DecimalField
    from django.db.models.functions import Coalesce
    from datetime import datetime as _datetime, date as _date

    user = request.user
    PLATFORM_START_YEAR = 2020
    YEARLY_DUES = 5000
    current_year = timezone.now().year

    # --- DUES DATA ---
    debt_info = DuesPayment.get_member_debt(user)
    dues_payments = DuesPayment.objects.filter(member=user).select_related("recorded_by").order_by("-year")
    total_dues_paid = dues_payments.aggregate(
        total=Coalesce(Sum("amount_paid"), Value(0, output_field=DecimalField()))
    )["total"]

    # Year-by-year status (raw, for grouping) — only from the member's own
    # join year onward. Years before they joined are never "owed" (matches
    # the same join-year-aware logic used in the Dues Tracker and Debtors
    # List, via DuesPayment.get_member_join_year()).
    join_year = DuesPayment.get_member_join_year(user)
    start_year = max(join_year, PLATFORM_START_YEAR)
    years = list(range(start_year, current_year + 1))
    year_status = []
    for year in years:
        payment = dues_payments.filter(year=year).first()
        year_status.append({
            "year": year,
            "status": "PAID" if payment else "OWED",
            "payment": payment,
        })

    # Group consecutive years with same status
    year_status_grouped = []
    if year_status:
        current_group = {
            "status": year_status[0]["status"],
            "start_year": year_status[0]["year"],
            "end_year": year_status[0]["year"],
            "payment": year_status[0]["payment"],
            "count": 1,
        }
        for ys in year_status[1:]:
            if ys["status"] == current_group["status"]:
                current_group["end_year"] = ys["year"]
                current_group["count"] += 1
                if ys["status"] == "PAID" and ys["payment"]:
                    current_group["payment"] = ys["payment"]
            else:
                current_group["total_amount"] = current_group["count"] * YEARLY_DUES
                year_status_grouped.append(current_group)
                current_group = {
                    "status": ys["status"],
                    "start_year": ys["year"],
                    "end_year": ys["year"],
                    "payment": ys["payment"],
                    "count": 1,
                }
        current_group["total_amount"] = current_group["count"] * YEARLY_DUES
        year_status_grouped.append(current_group)

    # Group dues by transaction (deposit-level)
    dues_txns = DuesPaymentTransaction.objects.filter(
        member=user
    ).select_related("recorded_by").order_by("-payment_date")

    dues_transactions_grouped = []
    for txn in dues_txns:
        dues_records = DuesPayment.objects.filter(
            transactions=txn
        ).values_list("year", flat=True).order_by("year")

        years_list = list(dues_records)
        if years_list:
            if len(years_list) == 1:
                year_display = str(years_list[0])
                reason = f"Yearly Dues — {year_display}"
            else:
                year_display = f"{years_list[0]}–{years_list[-1]}"
                has_prepaid = any(y > current_year for y in years_list)
                prepaid_label = " (Prepaid)" if has_prepaid else ""
                reason = f"Yearly Dues — {year_display}{prepaid_label}"
        else:
            reason = "Yearly Dues"

        dues_transactions_grouped.append({
            "transaction": txn,
            "reason": reason,
            "amount": txn.total_amount,
            "recorded_by": txn.recorded_by,
            "payment_date": txn.payment_date,
            "years": years_list,
            "is_prepaid": any(y > current_year for y in years_list) if years_list else False,
        })

    # --- DONATIONS DATA ---
    # Credit only the actual donor. `member` is the FK the donor is recorded
    # against; `created_by` is just who entered the record (an executive
    # recording on someone else's behalf must never get credit for it —
    # created_by is for audit trails only, never for attribution/totals).
    donations_qs = Income.objects.exclude(income_type="DUES").filter(
        Q(member=user) |
        Q(paid_by__icontains=user.full_name) |
        Q(paid_by__icontains=user.serial_number)
    ).select_related("created_by", "member").order_by("-created_at")

    total_donations = donations_qs.aggregate(
        total=Coalesce(Sum("amount"), Value(0, output_field=DecimalField()))
    )["total"]

    # --- COMBINED CONTRIBUTIONS ---
    total_contributions = total_dues_paid + total_donations

    # --- ALL PAYMENTS (unified: grouped dues + other income) ---
    all_payments_list = []

    # 1) Grouped dues transactions
    for item in dues_transactions_grouped:
        payment_dt = item["payment_date"]
        if isinstance(payment_dt, _date) and not isinstance(payment_dt, _datetime):
            payment_dt = _datetime.combine(payment_dt, _datetime.min.time())
        if payment_dt.tzinfo is None:
            payment_dt = timezone.make_aware(payment_dt)

        all_payments_list.append({
            "type": "dues_grouped",
            "created_at": payment_dt,
            "date_display": item["payment_date"],
            "reason": item["reason"],
            "amount": item["amount"],
            "recorded_by": item["recorded_by"],
            "is_prepaid": item["is_prepaid"],
            "income_type": "DUES",
        })

    # 2) Non-dues income — same donor-only attribution as donations_qs above.
    other_incomes = Income.objects.exclude(income_type="DUES").filter(
        Q(member=user) |
        Q(paid_by__icontains=user.full_name) |
        Q(paid_by__icontains=user.serial_number)
    ).select_related("created_by", "member").order_by("-created_at")

    for income in other_incomes:
        all_payments_list.append({
            "type": "income",
            "created_at": income.created_at,
            "date_display": income.created_at,
            "reason": income.reason,
            "amount": income.amount,
            "recorded_by": income.created_by,
            "income_type": income.income_type,
        })

    # Sort by date descending
    all_payments_list.sort(key=lambda x: x["created_at"], reverse=True)

    payments_paginator = Paginator(all_payments_list, 10)
    payments_page = request.GET.get("payments_page", 1)
    payments = payments_paginator.get_page(payments_page)

    # Notifications
    notifications = Notification.objects.filter(
        Q(recipient=user) | Q(is_global=True) | Q(recipient__isnull=True)
    ).order_by("-created_at")[:10]

    # Forms
    profile_form = FloorMemberProfileForm(instance=user)
    pin_form = ChangePINForm()

    context = {
        "user": user,
        "payments": payments,
        "total_paid": total_contributions,
        "total_dues_paid": total_dues_paid,
        "total_donations": total_donations,
        "debt_info": debt_info,
        "year_status_grouped": year_status_grouped,
        "yearly_dues": YEARLY_DUES,
        "current_year": current_year,
        "dues_transactions_grouped": dues_transactions_grouped,
        "donations": donations_qs,
        "notifications": notifications,
        "profile_form": profile_form,
        "pin_form": pin_form,
        "currency_symbol": getattr(settings, "OYA_SETTINGS", {}).get("CURRENCY_SYMBOL", "₦"),
    }
    return render(request, "accounts/profile.html", context)
    

@login_required
@require_POST
def profile_update(request):
    """Update own profile (phone, state)."""
    form = FloorMemberProfileForm(request.POST, request.FILES, instance=request.user)
    if form.is_valid():
        form.save()
        log_request_action(
            request,
            action="UPDATE",
            object_type="User",
            object_id=request.user.id,
            description=f"Updated profile for {request.user.serial_number}"
        )
        messages.success(request, "Profile updated successfully.")
    else:
        for error_list in form.errors.values():
            for error in error_list:
                messages.error(request, error)
    return redirect("accounts:profile")


@login_required
@require_POST
def change_pin(request):
    """Change own PIN."""
    form = ChangePINForm(request.POST, user=request.user)
    if form.is_valid():
        new_pin = form.cleaned_data["new_pin"]
        request.user.set_pin(new_pin)
        request.user.save()
        update_session_auth_hash(request, request.user)
        log_request_action(
            request,
            action="PIN_RESET",
            object_type="User",
            object_id=request.user.id,
            description="User changed their own PIN"
        )
        messages.success(request, "PIN updated successfully.")
    else:
        for error_list in form.errors.values():
            for error in error_list:
                messages.error(request, error)
    return redirect("accounts:profile")


@login_required
@require_http_methods(["GET"])
def user_search_ajax(request):
    """
    Shared AJAX autocomplete endpoint for selecting a User (used wherever a
    form needs to attach a record to a login account, e.g. finance income
    and yearly dues). Searches by full name, serial/membership number, and
    phone number. Powers the global member-autocomplete widget — see
    core/widgets.py and static/js/autocomplete.js.
    """
    search_term = request.GET.get("q", "").strip()
    if len(search_term) < 1:
        return JsonResponse({"results": []})

    users = User.objects.filter(is_active=True).filter(
        Q(serial_number__icontains=search_term) |
        Q(full_name__icontains=search_term) |
        Q(phone__icontains=search_term)
    )
    # A user account can stay is_active=True even after the linked Member
    # record is marked Removed — exclude those so removed members never
    # appear in this shared picker (finance income, dues, etc.). Admins
    # never appear here either — they manage/monitor, they don't pay dues,
    # donate, or otherwise act as members.
    users = exclude_admin_users(exclude_removed_users(users)).order_by("full_name")[:15]

    results = [
        {
            "id": u.id,
            "serial_number": u.serial_number,
            "full_name": u.full_name,
            "phone": u.phone,
            "role": u.role,
            "photo_url": u.photo.url if u.photo else ""
        }
        for u in users
    ]

    return JsonResponse({"results": results})