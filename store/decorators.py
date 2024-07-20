from functools import wraps
from django.contrib.auth.decorators import user_passes_test, login_required
from django.shortcuts import render


def superuser_required(view_func):
    """
    Decorator that requires the current user to be a superuser and logged in.
    If the user is not a superuser, it renders an "Access Denied" page.
    """
    @wraps(view_func)
    @user_passes_test(lambda u: u.is_superuser, login_url=None)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_superuser:
            return render(request, 'store/access_denied.html')
        return view_func(request, *args, **kwargs)

    return _wrapped_view
