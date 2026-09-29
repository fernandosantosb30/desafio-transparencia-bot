from __future__ import annotations

import argparse
import asyncio
import json
import sys

from pydantic import ValidationError
from app.core.logging import logger

from app.services.browser_pool import BrowserPool
from app.services.scraper import TIMEOUT_MESSAGE, TransparenciaScraper
from app.utils.errors import DomainError, NoResultsError


async def main() -> None:
    parser = argparse.ArgumentParser(description="Consulta o Portal da Transparência.")
    parser.add_argument("--termo", required=True, help="CPF, NIS ou nome da pessoa.")
    parser.add_argument("--filtro-social", action="store_true", help="Aplica o filtro de beneficiário de programa social.")
    args = parser.parse_args()

    scraper = TransparenciaScraper(browser_pool=BrowserPool(1))
    try:
        result = await scraper.consultar(args.termo, args.filtro_social)
    except (DomainError, ValidationError) as exc:
        logger.warning("Consulta interrompida: %s", type(exc).__name__)
        message = str(exc) if isinstance(exc, NoResultsError) else TIMEOUT_MESSAGE
        result = scraper._build_error_response(args.termo, message)
    print(json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False))
    if result.status == "erro":
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
