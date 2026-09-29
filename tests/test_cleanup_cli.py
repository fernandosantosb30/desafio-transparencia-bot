import json
from unittest.mock import AsyncMock

import pytest

from app import cli
from app.schemas.consulta import ConsultaRequest
from app.services import scraper as scraper_module
from app.services.scraper import TransparenciaScraper
from app.utils.errors import NoResultsError


async def test_browser_closes_when_context_creation_fails(monkeypatch):
    browser = AsyncMock()
    browser.new_context.side_effect = RuntimeError("context failure")
    playwright = AsyncMock()
    playwright.chromium.launch.return_value = browser
    manager = AsyncMock()
    manager.__aenter__.return_value = playwright
    monkeypatch.setattr(scraper_module, "async_playwright", lambda: manager)
    with pytest.raises(RuntimeError):
        await TransparenciaScraper()._run(ConsultaRequest(termo="Maria"))
    browser.close.assert_awaited_once()


async def test_cli_errors_remain_json(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["app.cli", "--termo", "Nome inexistente"])
    monkeypatch.setattr(TransparenciaScraper, "consultar", AsyncMock(side_effect=NoResultsError("Foram encontrados 0 resultados para o termo Nome inexistente")))
    with pytest.raises(SystemExit) as exc:
        await cli.main()
    assert exc.value.code == 1
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "erro"
    assert "0 resultados" in result["mensagem"]
