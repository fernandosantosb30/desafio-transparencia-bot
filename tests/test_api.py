from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.main import app
from app.schemas.consulta import ConsultaResponse
from app.utils.errors import NoResultsError, SearchTimeoutError
from pydantic import SecretStr


@pytest.fixture(autouse=True)
def local_api_without_key(monkeypatch):
    monkeypatch.setattr(routes.settings, "API_KEY", None)


def test_api_key_is_required_when_configured(monkeypatch):
    monkeypatch.setattr(routes.settings, "API_KEY", SecretStr("test-key"))
    assert client.post("/consulta", json={"termo": "Teste"}).status_code == 401
    assert client.post("/consulta", json={"termo": "Teste"}, headers={"X-API-Key": "wrong"}).status_code == 401

    async def fake_consultar(termo, filtro_beneficiario_social=False):
        return ConsultaResponse(id_consulta="auth-test", status="erro", termo=termo)

    monkeypatch.setattr(routes._scraper, "consultar", fake_consultar)
    assert client.post("/consulta", json={"termo": "Teste"}, headers={"X-API-Key": "test-key"}).status_code == 200

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.parametrize("term", ["", "   ", "\t\n", "x" * 201])
def test_invalid_term(term):
    assert client.post("/consulta", json={"termo": term}).status_code == 422


def test_consulta_success(monkeypatch) -> None:
    async def fake_consultar(termo: str, filtro_beneficiario_social: bool = False):
        return ConsultaResponse(
            id_consulta="abc-123",
            status="sucesso",
            data_hora=datetime.now(timezone.utc),
            termo=termo,
            dados_pessoa={"nome": "Maria da Silva", "cpf": "123.456.789-09"},
            beneficios=[],
            evidencia_base64="ZmFrZQ==",
        )

    monkeypatch.setattr(routes._scraper, "consultar", fake_consultar)

    response = client.post("/consulta", json={"termo": "12345678909", "filtro_beneficiario_social": False})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "sucesso"
    assert data["dados_pessoa"]["nome"] == "Maria da Silva"


def test_consulta_no_results(monkeypatch) -> None:
    async def fake_consultar(termo: str, filtro_beneficiario_social: bool = False):
        raise NoResultsError(f"Foram encontrados 0 resultados para o termo {termo}")

    monkeypatch.setattr(routes._scraper, "consultar", fake_consultar)

    response = client.post("/consulta", json={"termo": "Nome inexistente", "filtro_beneficiario_social": False})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "erro"
    assert "0 resultados" in data["mensagem"]


@pytest.mark.parametrize(
    ("payload", "expected_status", "expected_message", "expected_name"),
    [
        ({"termo": "12345678909", "filtro_beneficiario_social": False}, "sucesso", None, "Maria da Silva"),
        ({"termo": "99999999999", "filtro_beneficiario_social": False}, "erro", "Não foi possível retornar os dados no tempo de resposta solicitado", None),
        ({"termo": "Maria da Silva", "filtro_beneficiario_social": False}, "sucesso", None, "Maria da Silva"),
        ({"termo": "Nome inexistente", "filtro_beneficiario_social": False}, "erro", "Foram encontrados 0 resultados para o termo Nome inexistente", None),
        ({"termo": "Silva", "filtro_beneficiario_social": True}, "sucesso", None, "Maria da Silva"),
    ],
)
def test_consulta_scenarios(monkeypatch, payload, expected_status, expected_message, expected_name) -> None:
    async def fake_consultar(termo: str, filtro_beneficiario_social: bool = False):
        if termo == "99999999999":
            raise SearchTimeoutError("Não foi possível retornar os dados no tempo de resposta solicitado")
        if termo == "Nome inexistente":
            raise NoResultsError(f"Foram encontrados 0 resultados para o termo {termo}")
        return ConsultaResponse(
            id_consulta="scenario-id",
            status="sucesso",
            data_hora=datetime.now(timezone.utc),
            termo=termo,
            dados_pessoa={"nome": "Maria da Silva", "cpf": "123.456.789-09"},
            beneficios=[],
            evidencia_base64="ZmFrZQ==",
        )

    monkeypatch.setattr(routes._scraper, "consultar", fake_consultar)
    response = client.post("/consulta", json=payload)
    data = response.json()
    assert response.status_code == 200
    assert data["status"] == expected_status
    if expected_message:
        assert data["mensagem"] == expected_message
    if expected_name:
        assert data["dados_pessoa"]["nome"] == expected_name
