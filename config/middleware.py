from django.contrib import messages
from django.urls import resolve

class AuthMessageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            name = resolve(request.path_info).url_name
        except Exception:
            return response
        if name == "login" and request.user.is_authenticated:
            messages.success(request, "Welcome back!")
        elif name == "logout":
            messages.info(request, "You have been logged out.")
        return response
