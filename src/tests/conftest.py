import os
import time

import vcr

cassette_dir = "tests/cassettes"


def program_vcr():
    for cassette in os.listdir(cassette_dir):
        if "yaml" in cassette:  # Only delete the casette files
            delete_stale_cassette(cassette_name=cassette)

    _vcr = vcr.VCR(
        cassette_library_dir=cassette_dir,
        record_mode="new_episodes",
    )

    return _vcr


def delete_stale_cassette(
    cassette_name: str, delete_if_older_than_days: int = 30
) -> None:
    """We're using VCR.py to record the request / responses to the various manufacturer
    APIs, in order to facilitate offline testing, less-flakey and deterministic tests.
    As the manufacturer APIs are not under our control, I want to occasionally refresh
    the API responses to ensure our tests pass against the most recent version of a
    manufacturer API. If a VCR.py cassette is > delete_if_older_than_days days old,
    remove it before starting a test.

    Args:
        cassette_name (str): Name of the cassette file to delete.
        delete_if_older_than_days (int, optional): Delete a cassette file if older than
         this value. Defaults to 30.
    """

    cassette_file = f"{cassette_dir}/{cassette_name}"
    file_age_in_sec = time.time() - os.path.getmtime(cassette_file)

    if file_age_in_sec > (delete_if_older_than_days * 60 * 60):
        print(f"Deleting {cassette_file}")
        os.remove(cassette_file)
