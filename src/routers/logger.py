import google.cloud.logging
from fastapi import APIRouter
from google.cloud import error_reporting
from pydantic import BaseModel


class ErrorMessage(BaseModel):
    errorMessage: str
    additionalData: dict | None = None


router = APIRouter(prefix="/api")


# Setup info level logging to GCP Cloud Logging
client = google.cloud.logging.Client()
gcp_logger = client.logger(name="evfinder")


@router.post("/logger/error")
async def get_manufacturer_inventory(error: ErrorMessage) -> dict:
    """A helper function which accepts an error log message and writes that message to
    GCP Error Reporting.

    This function can be called directly through send_gcp_error_message() which accepts
    one argument, a string containing the message to be logged.

    Keyword arguments:
    errorMessage -- the error message to be logged

    This is also exposed through /api/logger/error, which accepts a POST request
    containing a JSON body with the information to be logged. Regardless of logging
    success/failure a 200/OK is returned. This was designed to be fire and forget, so the
    actual response back to the caller isn't used.
    """

    # Setup error logging to GCP Error Reporting
    error_client = error_reporting.Client(version=error.additionalData["appVersion"])

    # The HTTPContext class is automatically parsed by the GCP Error Reporting service,
    # so using HTTPContext to supply some EVFinder specific information.
    http_context = error_reporting.HTTPContext(
        user_agent=error.additionalData["userAgent"],
        referrer=error.additionalData["appVersion"],
    )
    error_client.report(
        message=f"{error.errorMessage} {error.additionalData}",
        http_context=http_context,
    )

    return {"status": "OK"}
