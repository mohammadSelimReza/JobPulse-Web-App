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

        # Handle response data/errors
        extra_info = ""
        if status_code >= 400:
            try:
                if hasattr(response, 'data') and response.data:
                    extra_info = f" - Error: {dict(response.data)}"
                elif response.content:
                    extra_info = f" - Error: {response.content.decode('utf-8')[:200]}"
            except Exception:
                extra_info = " - Error: Unknown"
        else:
            # For 200 responses, if it's the OTP request, show the code in logs for dev convenience
            try:
                if hasattr(response, 'data') and isinstance(response.data, dict):
                    if 'code' in response.data:
                        extra_info = f" [OTP: {response.data['code']}]"
                    elif 'message' in response.data:
                        extra_info = f" - {response.data['message']}"
            except Exception:
                pass

        # Format: [ Date ] [ Time ] : [ User ] - [api] - status code - [ extra info ]
        log_message = f"[ {date_str} ] [ {time_str} ] : [ {user_str} ] - [{api_path}] - {status_code}{extra_info}"
        
        # Print directly to stdout for docker logs
        print(log_message, flush=True)

        return response
