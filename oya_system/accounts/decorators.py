from django.shortcuts import redirect


def login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get('member_id'):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.session.get('member_role') != 'admin':
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper
