from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from app.core.config import settings
from app.core.logging import logger, set_request_id
from app.schemas.consulta import ConsultaRequest, ConsultaResponse
from app.services.browser_pool import BrowserPool
from app.services.scraper import TransparenciaScraper
from app.utils.errors import NoResultsError, PortalBlockedError, SearchTimeoutError

router = APIRouter()
_scraper = TransparenciaScraper(browser_pool=BrowserPool(settings.MAX_CONCURRENT_REQUESTS))


@router.get("/health")
async def health() -> dict[str, str | bool]:
    return {"status": "ok", "service": settings.APP_NAME, "headless": settings.PLAYWRIGHT_HEADLESS}


@router.post("/consulta", response_model=ConsultaResponse)
async def consulta(request: Request, payload: ConsultaRequest) -> ConsultaResponse:
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    set_request_id(request_id)
    logger.info("Consulta recebida")

    try:
        result = await _scraper.consultar(payload.termo, payload.filtro_beneficiario_social)
        return result
    except NoResultsError as exc:
        return ConsultaResponse(
            id_consulta=str(uuid.uuid4()),
            status="erro",
            data_hora=datetime.now(timezone.utc),
            termo=payload.termo,
            mensagem=str(exc),
        )
    except (PortalBlockedError, SearchTimeoutError):
        return ConsultaResponse(
            id_consulta=str(uuid.uuid4()),
            status="erro",
            data_hora=datetime.now(timezone.utc),
            termo=payload.termo,
            mensagem="Não foi possível retornar os dados no tempo de resposta solicitado",
        )
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - broad safety net
        logger.exception("Erro interno ao processar consulta")
        return ConsultaResponse(
            id_consulta=str(uuid.uuid4()),
            status="erro",
            data_hora=datetime.now(timezone.utc),
            termo=payload.termo,
            mensagem="Não foi possível retornar os dados no tempo de resposta solicitado",
        )
