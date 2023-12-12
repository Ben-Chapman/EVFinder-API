from fastapi import Query


class CommonInventoryQueryParams:
    """Defining the query parameters which are common across all inventory API calls.

    When included in a Fast API route, Fast API will use this class to validate that all
    query params are present in the request, and they validate through Query() rules.
    https://fastapi.tiangolo.com/tutorial/dependencies/classes-as-dependencies/#classes-as-dependencies
    """

    valid_models = [
        "^Ioniq(%20|\+|\s|\-)5$",  # Hyundai Ioniq 5  # noqa: W605
        "^Ioniq(%20|\+|\s|\-)6$",  # Hyundai Ioniq 6  # noqa: W605
        "^Kona(%20|\+|\s)Ev$",  # Hyundai Kona EV  # noqa: W605
        "^N$",  # Kia EV6
        "^V$",  # Kia Niro EV
        "^GV60$",  # Genesis GV60
        "^ELECTRIFIED-G80$",  # Genesis Electrified G80
        "^ELECTRIFIED-GV70$",  # Genesis Electrified GV70
        "^ID.4$",  # VW ID.4
        "^mache$",  # Ford Mustang Mach-E
        r"^f-150(%20|\+|\s|\-)lightning",  # Ford F-150 Lightning
        "^Blazer EV$",  # Chevrolet Blazer EV
        "^Bolt EV$",  # Chevrolet Bolt EV
        "^Bolt EUV$",  # Chevrolet Bolt EUV
        "^Equinox EV$",  # Chevrolet Equinox EV
        "^Silverado EV$",  # Chevrolet Silverado EV
        "^etron$",  # Audi e-tron
        "^etrongt$",  # Audi e-tron GT
        "^q4$",  # Audi Q4 e-tron
        "^s?q8etron$",  # Audi Q8 e-tron, SQ8 e-tron
        "^i4$",  # BMW i4
        "^i5$",  # BMW i5
        "^i7$",  # BMW i7
        "^9$",  # BMW ix
    ]

    def __init__(
        self,
        # https://facts.usps.com/42000-zip-codes/. Starting zip code is 00501
        zip: int = Query(ge=501, le=99950),
        year: int = Query(ge=2022, le=2024),
        radius: int = Query(gt=0, lt=1000),
        model: str = Query(regex="|".join(valid_models)),
    ):
        # Zip is passed in as a query parameter string. When casting to an int, the
        # leading 0s are stripped, so "00501" becomes 501. So, padding with 0s as needed.
        self.zip = f"{zip:05}"
        self.year = year
        self.radius = radius
        self.model = model


class CommonVinQueryParams:
    """Defining the query parameters which are common across all inventory API calls.

    When included in a Fast API route, Fast API will use this class to validate that all
    query params are present in the request, and they validate through Query() rules.
    https://fastapi.tiangolo.com/tutorial/dependencies/classes-as-dependencies/#classes-as-dependencies
    """

    valid_models = CommonInventoryQueryParams.valid_models

    def __init__(
        self,
        vin: str,
    ):
        self.vin = vin
        self.year = CommonInventoryQueryParams.year
        self.model = CommonInventoryQueryParams.model
