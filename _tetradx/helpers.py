from rest_framework.decorators import APIView
from rest_framework.exceptions import APIException


def api_exception(message, custom_code=None):
    class ValidationException(APIException):
        status_code = custom_code if custom_code else 400
        default_detail = {
            "status": "error",
            "code": status_code,
            "detail": message,
        }

    return ValidationException()


class BaseAPIView(APIView):
    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)

        user = request.user

        if user.is_authenticated and not user.is_active and not user.is_superuser:
            raise api_exception(
                "Password change required. Please change your password before proceeding.",
                custom_code=403,
            )

        return response
