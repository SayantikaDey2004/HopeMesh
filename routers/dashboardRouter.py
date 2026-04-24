from fastapi import APIRouter, Depends

from app.Validation.dashboardValidation import AutoMatchNowValidationSchema
from app.core.dependencies import get_current_ngo_id
from app.models.dashboardSchema import AutoMatchResultSchema, DashboardSchema
from app.services.dashboard.Dashboard import auto_match_now, get_dashboard_summary

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardSchema)
async def dashboard_overview_controller(
    ngo_id: str = Depends(get_current_ngo_id),
):
    return await get_dashboard_summary(ngo_id)


@router.post("/auto-match-now", response_model=AutoMatchResultSchema)
async def auto_match_now_controller(
    data: AutoMatchNowValidationSchema,
    ngo_id: str = Depends(get_current_ngo_id),
):
    return await auto_match_now(data, ngo_id)
