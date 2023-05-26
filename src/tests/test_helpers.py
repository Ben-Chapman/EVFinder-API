import vcr


def generate_test_query_params() -> dict:
    """Provides a dict of default query params to be used for API tests"""
    return {
        "model": "N",
        "year": "2023",
        "zip": "90210",
        "radius": "500",
    }


def program_vcr():
    _vcr = vcr.VCR(
        cassette_library_dir="tests/cassettes",
        record_mode="new_episodes",
    )

    return _vcr
