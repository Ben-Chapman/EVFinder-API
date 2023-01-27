from fastapi import Query


class CommonInventoryQueryParams:
    """Defining the query parameters which are common across all inventory API calls.
    Fast API will use this class to validate that all query params are present in the
    request, and they validate through the defined Query() rules.
    https://fastapi.tiangolo.com/tutorial/dependencies/classes-as-dependencies/#classes-as-dependencies
    """

    valid_models = [
        "^Ioniq(%20|\+|\s)6$",  # noqa: W605
        "^Ioniq(%20|\+|\s)5$",  # noqa: W605
        "^Ioniq(%20|\+|\s)Phev$",  # noqa: W605
        "^Kona(%20|\+|\s)Ev$",  # noqa: W605
        "^Santa(%20|\+|\s)Fe(%20|\+|\s)Phev$",  # noqa: W605
        "^Tucson(%20|\+|\s)Phev$",  # noqa: W605
        "^N$",  # EV6
        "^V$",  # Niro EV
        "^F$",  # Niro Plug-in Hybrid
        "^R$",  # Sportage Plug-in Hybrid
        "^T$",  # Sorento Plug-in Hybrid
        "^GV60$",  # Genesis GV60
        "^ElectrifiedG80$",  # Genesis Electrified G80
        "^ID.4$",  # VW ID.4
        "^mache$",  # Ford Mustang Mach-E
        "^Bolt EV$",  # Chevrolet Bolt EV
        "^Bolt EUV$",  # Chevrolet Bolt EUV
        "^etron$",  # Audi e-tron
        "^etrongt$",  # Audi e-tron GT
        "^q4$",  # Audi Q4 e-tron
    ]

    def __init__(
        self,
        # https://facts.usps.com/42000-zip-codes/
        # Starting zip code is 00501
        zip: int = Query(ge=501, le=99950),
        year: int = Query(ge=2022, le=2023),
        radius: int = Query(gt=0, lt=1000),
        model: str = Query(regex="|".join(valid_models)),
    ):
        self.zip = zip
        self.year = year
        self.radius = radius
        self.model = model
