from fastapi import Query


class CommonInventoryQueryParams:
    """Defining the query parameters which are common across all inventory API calls.
    https://fastapi.tiangolo.com/tutorial/dependencies/classes-as-dependencies/#classes-as-dependencies

    """

    valid_models = [
        "Ioniq%205",
        "Ioniq%206",
        "Ioniq%20Phev",
        "Kona%20Ev",
        "Santa%20Fe%20Phev",
        "Tucson%20Phev",
        "N",  # EV6
        "V",  # Niro EV
        "F",  # Niro Plug-in Hybrid
        "R",  # Sportage Plug-in Hybrid
        "T",  # Sorento Plug-in Hybrid
        "GV60",  # Genesis GV60
        "ElectrifiedG80",  # Genesis Electrified G80
        "ID.4",  # VW ID.4
        "mache",  # Ford Mustang Mach-E
        "Bolt EV",  # Chevrolet Bolt EV
        "Bolt EUV",  # Chevrolet Bolt EUV
        "etron",  # Audi e-tron
        "etrongt",  # Audi e-tron GT
        "q4",  # Audi Q4 e-tron
    ]

    def __init__(
        self,
        zip: int = Query(gt=501, lt=99951),
        year: int = Query(gt=2021, lt=2024),
        radius: int = Query(gt=0, lt=1000),
        model: str = Query(regex="|".join(valid_models)),
    ):
        self.zip = zip
        self.year = year
        self.radius = radius
        self.model = model
