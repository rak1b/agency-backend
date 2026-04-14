
from rest_framework.renderers import JSONRenderer
from rest_framework import status as drf_status
import logging
logger = logging.getLogger('django')



class CustomRenderer(JSONRenderer):

    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get('response')
        status_code = response.status_code if response else 200

        # Handle no content (204) safely — send 200 with a message instead
        if status_code == drf_status.HTTP_204_NO_CONTENT:
            response.status_code = drf_status.HTTP_200_OK
            custom_response = {
                "status": "success",
                "code": drf_status.HTTP_200_OK,
                "message": self._get_success_message(renderer_context),
                "data": None
            }
            return super().render(custom_response, accepted_media_type, renderer_context)

        # Log errors for non-2xx responses
        if not str(status_code).startswith("2"):
            logger.error(data)

        custom_response = {
            "code": status_code,
            "status": "success" if str(status_code).startswith("2") else "error",
            "message": None,
            "data": None,
            "errors": None
        }

        # Success response
        if str(status_code).startswith("2"):
            if isinstance(data, dict):
                if "data" in data:
                    custom_response["data"] = data["data"]
                elif "detail" in data:
                    custom_response["message"] = data.get("detail")
                    custom_response["data"] = None
                else:
                    custom_response["data"] = data
            else:
                custom_response["data"] = data
        else:
            # Error response
            if isinstance(data, dict):
                if "detail" in data:
                    custom_response["message"] = data.get("detail")
                elif "message" in data:
                    custom_response["message"] = data.get("message")
                else:
                    custom_response["message"] = "Validation error"
                    custom_response["errors"] = data
            else:
                custom_response["message"] = "Validation error"
                custom_response["errors"] = data

        return super().render(custom_response, accepted_media_type, renderer_context)

    def _get_success_message(self, context):
        """
        Returns a custom message based on the request path for 204/empty-body operations.
        Adjusts language for soft delete, hard delete, restore.
        """
        request = context.get('request')
        if not request:
            return "Operation completed successfully"

        path = request.path.lower()

        if 'hard-delete' in path:
            return "Object hard deleted successfully"
        elif 'retrieve-soft-deleted' in path or 'restore' in path:
            return "Object restored successfully"
        elif request.method == "DELETE":
            return "Object soft deleted successfully"

        return "Request successfully executed"
