from typing import Optional, Callable
from flask import request, Response, session
from kinde_sdk.core.framework.framework_context import FrameworkContext
import logging

logger = logging.getLogger(__name__)

class FrameworkMiddleware:
    """
    Middleware for handling Flask-specific request/response processing.
    """
    
    @staticmethod
    def before_request() -> None:
        """
        Process the request before it reaches the route handler.
        Sets up the framework context with the current request.
        """
        FrameworkContext.set_request(request)
        
    @staticmethod
    def after_request(response: Response) -> Response:
        """
        Process the response after it leaves the route handler.
        
        Args:
            response (Response): The Flask response object.
            
        Returns:
            Response: The processed response.
        """
        try:
            # If any cookies were queued on the request by storage, set them on the response
            cookies_to_set = getattr(request, "_kinde_cookies_to_set", None)
            if isinstance(cookies_to_set, dict):
                for name, val in cookies_to_set.items():
                    try:
                        response.set_cookie(name, val, httponly=True, secure=True, samesite="Lax")
                    except Exception:
                        # Best-effort; continue setting other cookies
                        pass
        finally:
            # Clear the framework context regardless of cookie handling outcome
            FrameworkContext.clear_request()
        return response