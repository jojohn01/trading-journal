from django.contrib import messages
from django.urls import resolve

"""
middleware.py

Custom Django middleware for displaying authentication-related messages to users.
This middleware adds success or info messages upon login and logout events,
using Django's messages framework.
"""

class AuthMessageMiddleware:
    """
    Middleware that attaches authentication-related messages to the request.
    On successful login, displays a welcome message.
    On logout, displays an informational message.

    Args:
        get_response (callable): The next middleware or view in the chain.
    """
    def __init__(self, get_response):
        """
        Initialize the middleware with the next response handler.

        Args:
            get_response (callable): The next middleware or view in the chain.
        """
        self.get_response = get_response

    def __call__(self, request):
        """
        Process the incoming request and attach messages based on authentication events.

        Args:
            request (HttpRequest): The incoming HTTP request.

        Returns:
            HttpResponse: The HTTP response after processing.
        """
        response = self.get_response(request)
        try:
            name = resolve(request.path_info).url_name
        except Exception:
            # If URL cannot be resolved, skip message handling.
            return response
        if name == "login" and request.user.is_authenticated:
            messages.success(request, "Welcome back!")
        elif name == "logout":
            messages.info(request, "You have been logged out.")
        return response
