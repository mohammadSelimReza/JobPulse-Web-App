import time
from datetime import datetime

class APILoggingMiddleware:
    """
    Middleware that logs API requests, responses, and errors in the specific format:
    [ Date ] [ Time ] : [ User ] - [api] - status code - [ if error :then show error]
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # We only care about logging API requests
        if not request.path.startswith('/api/'):
            return self.get_response(request)

        # Process the request
        response = self.get_response(request)

        # Build log string
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

        # Determine user
        user_str = "Anonymous"
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_str = getattr(request.user, 'phone_number', str(request.user.id))

        status_code = response.status_code
        api_path = request.path

        # Handle errors
        error_msg = ""
        if status_code >= 400:
            # Try to grab the error from the JSON response if DRF gave one
            try:
                # Many DRF responses are rendered JSON
                if hasattr(response, 'data') and response.data:
                    error_msg = f" - Error: {dict(response.data)}"
                elif response.content:
                    error_msg = f" - Error: {response.content.decode('utf-8')[:200]}"
            except Exception:
                error_msg = " - Error: Unknown"

        # Format: [ Date ] [ Time ] : [ User ] - [api] - status code - [ if error :then show error]
        log_message = f"[ {date_str} ] [ {time_str} ] : [ {user_str} ] - [{api_path}] - {status_code}{error_msg}"
        
        # Print directly to stdout for docker logs
        print(log_message, flush=True)

        return response
