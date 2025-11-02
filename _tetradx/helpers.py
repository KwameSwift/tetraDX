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
