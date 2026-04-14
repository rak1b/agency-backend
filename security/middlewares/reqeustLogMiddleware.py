import json
import time
import logging
from datetime import datetime
from django.utils.deprecation import MiddlewareMixin

# Configure logging
logger = logging.getLogger('django_request')
logging.basicConfig(
    filename='request_response.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class RequestResponseLoggerMiddleware(MiddlewareMixin):
    def process_request(self, request):
        """
        Process incoming request and store details
        """
        request.start_time = time.time()  # Track execution time
        request_body = self.get_request_body(request)

        log_data = {
            "method": request.method,
            "timestamp": str(datetime.now()),
            "path": request.path,
            "remote_ip": self.get_client_ip(request),
            "headers": dict(request.headers),
            "body": request_body,
        }
        # logger.info(f"REQUEST: {json.dumps(log_data, indent=2)}")

    def process_response(self, request, response):
        """
        Process outgoing response and store details
        """
        execution_time = round((time.time() - request.start_time) * 1000, 2)
        response_body = self.get_response_body(response)

        # Convert response body to string and limit size
        response_body_str = json.dumps(response_body) if isinstance(response_body, dict) else str(response_body)
        response_body_str = response_body_str[:500]  # Limit log size

        log_data = {
            "status_code": response.status_code,
            "execution_time_ms": execution_time,
            "response_body": response_body_str,  
        }
        # logger.info(f"RESPONSE: {json.dumps(log_data, indent=2)}")

        return response

    def get_request_body(self, request):
        """
        Get request body safely
        """
        try:
            if request.method in ["POST", "PUT", "PATCH"]:
                content_type = request.content_type
                
                # Handle file uploads
                if 'multipart/form-data' in content_type:
                    return {
                        'files': list(request.FILES.keys()),
                        'data': dict(request.POST)
                    }
                
                # Handle JSON data
                if 'application/json' in content_type and request.body:
                    return json.loads(request.body.decode("utf-8"))
                
                # Handle form data
                if 'application/x-www-form-urlencoded' in content_type:
                    return dict(request.POST)
                
                return {}
        except Exception as e:
            return f"[Error processing request body: {str(e)}]"

        return {}

    def _normalized_content_type(self, response):
        """Content-Type without parameters (e.g. charset), lowercased."""
        header = response.get("Content-Type") or ""
        return header.split(";")[0].strip().lower()

    def _response_body_is_binary(self, content_type):
        """
        True when the body is not safe to decode as UTF-8 for logging (files, images, xlsx, etc.).
        Vendor JSON types (*+json) stay text/JSON, not binary.
        """
        if not content_type:
            return False
        if content_type == "application/json" or content_type.endswith("+json"):
            return False
        binary_prefixes = (
            "application/octet-stream",
            "application/pdf",
            "application/zip",
            "application/x-",
            "image/",
            "video/",
            "audio/",
            "font/woff",
        )
        if any(content_type.startswith(p) for p in binary_prefixes):
            return True
        # Excel, Office Open XML, and most other vendor/binary MIME types
        if content_type.startswith("application/vnd.openxmlformats"):
            return True
        if content_type.startswith("application/vnd.ms-"):
            return True
        if content_type.startswith("application/vnd.") and not content_type.endswith("+json"):
            return True
        return False

    def get_response_body(self, response):
        """
        Get response body safely for logging. Never decode binary responses as UTF-8.
        """
        if not hasattr(response, "content"):
            return "[No Content]"

        raw = response.content
        if raw is None:
            return "[No Content]"

        content_type = self._normalized_content_type(response)

        # JSON (including application/*+json)
        if content_type == "application/json" or content_type.endswith("+json"):
            try:
                return json.loads(raw.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return "[Invalid JSON]"

        if self._response_body_is_binary(content_type):
            type_suffix = f", type: {content_type}" if content_type else ""
            return f"[Binary response, {len(raw)} bytes{type_suffix}]"

        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            return f"[Non-UTF-8 or binary, {len(raw)} bytes]"

        if len(text) > 500:
            return text[:500] + "..."
        return text

    def get_client_ip(self, request):
        """
        Extract client IP address
        """
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0]
        return request.META.get("REMOTE_ADDR", "")
