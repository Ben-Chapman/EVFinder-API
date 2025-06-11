from fastapi import Query


class CommonInventoryQueryParams:
    """Defining the query parameters which are common across all inventory API calls.

    When included in a Fast API route, Fast API will use this class to validate that all
    query params are present in the request, and they validate through Query() rules.
    https://fastapi.tiangolo.com/tutorial/dependencies/classes-as-dependencies/#classes-as-dependencies
    """

    valid_models = [
        r"^Ioniq(%20|\+|\s|\-)5((%20|\+|\-)N)?$",  # Hyundai Ioniq 5 and 5 N  # noqa: W605
        r"^Ioniq(%20|\+|\s|\-)(6|9)$",  # Hyundai Ioniq 6, 9  # noqa: W605
        r"^Kona(%20|\+|\s)Ev$",  # Hyundai Kona EV  # noqa: W605
        "^N$",  # Kia EV6
        "^V$",  # Kia Niro EV
        "^P$",  # Kia EV9
        "^GV60$",  # Genesis GV60
        "^ELECTRIFIED-G80$",  # Genesis Electrified G80
        "^ELECTRIFIED-GV70$",  # Genesis Electrified GV70
        "^ID.4$",  # VW ID.4
        "^ID. Buzz$",  # VW ID.BUZZ
        "^mache$",  # Ford Mustang Mach-E
        r"^f-150(%20|\+|\s|\-)lightning",  # Ford F-150 Lightning
        "^Blazer EV$",  # Chevrolet Blazer EV
        "^Bolt EV$",  # Chevrolet Bolt EV
        "^Bolt EUV$",  # Chevrolet Bolt EUV
        "^Equinox EV$",  # Chevrolet Equinox EV
        "^Silverado EV$",  # Chevrolet Silverado EV
        "^etron$",  # Audi e-tron
        "^etrongt$",  # Audi e-tron GT
        "^q(4|6)$",  # Audi Q4 e-tron, Q6 e-tron
        "^s?q(6|8)etron$",  # Audi Q8 e-tron, SQ8 e-tron,SQ6 e-tron
        "^i4$",  # BMW i4
        "^i5$",  # BMW i5
        "^i7$",  # BMW i7
        "^9$",  # BMW ix
        r"^sierra(%20|\+|\s|\-)ev",  # GMC Sierra EV
        r"^hummer(%20|\+|\s|\-)ev(%20|\+|\s|\-)pickup",  # GMC HUMMER EV Pickup
        r"^hummer(%20|\+|\s|\-)ev(%20|\+|\s|\-)suv",  # GMC HUMMER EV SUV
        r"^escalade(%20|\+|\s|\-)iq",  # Cadillac Escalade IQ
        "lyriq",  # Cadillac Lyriq
        "optiq",  # Cadillac Optiq
        "vistiq",  # Cadillac Vistiq
    ]

    def __init__(
        self,
        # https://facts.usps.com/42000-zip-codes/. Starting zip code is 00501
        zip: int = Query(ge=501, le=99950),
        year: int = Query(ge=2022, le=2026),
        radius: int = Query(gt=0, le=500),
        model: str = Query(pattern="|".join(valid_models)),
    ):
        # Zip is passed in as a query parameter string. When casting to an int, the
        # leading 0s are stripped, so "00501" becomes 501. Padding with 0s as needed.
        self.zip = f"{zip:05}"  # noqa: E231
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
