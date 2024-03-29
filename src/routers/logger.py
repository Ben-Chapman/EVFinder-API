from fastapi import status, APIRouter, BackgroundTasks

# from google.cloud import error_reporting
from pydantic import BaseModel


class ErrorMessage(BaseModel):
    errorMessage: str
    userAgent: str
    appVersion: str


router = APIRouter(prefix="/api")


@router.post(
    "/logger/error",
    status_code=status.HTTP_202_ACCEPTED,
)
async def accept_application_error(
    error: ErrorMessage,
    background_tasks: BackgroundTasks,
):
    """A helper function which accepts an error log message and writes that message to
    GCP Error Reporting through the send_error_to_gcp() background task.

    This API endpoint accepts a POST request containing a JSON body with the information
    to be logged. Regardless of logging success/failure a 200/OK is returned. This was
    designed to be fire and forget, so the actual response back to the caller isn't used.

    Keyword arguments:
    errorMessage -- the error message to be logged
    """

    background_tasks.add_task(send_error_to_gcp, error)
    return {"status": "OK"}


def send_error_to_gcp(error, http_context=None):
    """A FastAPI Background task which sends the error to GCP Error Reporting"""

    from google.cloud import error_reporting

    if type(error) is str:
        error_client = error_reporting.Client()
        context = error_reporting.HTTPContext(
            method=http_context["method"],
            url=http_context["url"],
            user_agent=http_context["user_agent"],
            response_status_code=http_context["status_code"],
        )
        try:
            error_client.report(message=error, http_context=context)
        except Exception:
            pass
    else:
        # Setup error logging to GCP Error Reporting
        error_client = error_reporting.Client(version=error.appVersion)

        # The HTTPContext class is automatically parsed by the GCP Error Reporting service,
        # so using HTTPContext to supply some EVFinder specific information.
        http_context = error_reporting.HTTPContext(
            user_agent=error.userAgent,
            referrer=error.appVersion,
        )
        try:
            error_client.report(
                message=f"{error.errorMessage}",
                http_context=http_context,
            )
        except Exception:
            pass
