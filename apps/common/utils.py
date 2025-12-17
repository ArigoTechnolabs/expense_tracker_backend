from rest_framework.response import Response


def success_response(message="Success", data=None):
    """
    Return a success response with a message and optional data.
    """
    payload = {
        "success": True,
        "message": message,
        "data": [] if data is None else data,
    }
    return Response(payload, status=200)


def error_response(message="Error", data=None):
    """
    Return a error response with a message and optional data
    """
    payload = {
        "success": False,
        "message": message,
        "data": [] if data is None else data,
    }
    return Response(payload, status=200)


def first_error_message(detail):
    """
    Extract the first validation error and convert it into a clean,
    human-friendly message like:
    - "First name is required"
    - "Enter a valid email address"
    """
    if isinstance(detail, dict):
        for field, errors in detail.items():
            error_msg = None

            if isinstance(errors, (list, tuple)) and errors:
                error_msg = errors[0]
            elif isinstance(errors, str):
                error_msg = errors

            if error_msg:
                field_label = field.replace("_", " ").capitalize()

                if "this field is required" in error_msg.lower():
                    return f"{field_label} is required"

                if "enter a valid email address" in error_msg.lower():
                    return "Enter a valid email address"

                return error_msg

    if isinstance(detail, (list, tuple)) and detail:
        return detail[0]

    return str(detail)
