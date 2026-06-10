from fastapi import APIRouter, Depends

from app.api.deps import get_infra_registry
from app.infrastructure.adapters.registry import InfrastructureAdapterRegistry

router = APIRouter()


@router.get("")
async def list_infrastructure_adapters(registry: InfrastructureAdapterRegistry = Depends(get_infra_registry)):
    return registry.list_adapters()
