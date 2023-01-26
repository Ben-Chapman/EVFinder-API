from fastapi import APIRouter, Depends
from libs.common_query_params import CommonInventoryQueryParams

router = APIRouter(prefix="/api")


@router.get("/inventory/hyundai")
async def testing(params: CommonInventoryQueryParams = Depends()):

    return params.zip, params.year
