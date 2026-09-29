from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConsultaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    termo: str = Field(..., min_length=1, max_length=200)
    filtro_beneficiario_social: bool = False

    @field_validator("termo", mode="before")
    @classmethod
    def normalize_term(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class Beneficio(BaseModel):
    tipo: str
    detalhes: dict[str, Any] = Field(default_factory=dict)


class ConsultaResponse(BaseModel):
    id_consulta: str
    status: Literal["sucesso", "erro"]
    data_hora: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    termo: str
    mensagem: str | None = None
    dados_pessoa: dict[str, Any] | None = None
    beneficios: list[Beneficio] = Field(default_factory=list)
    evidencia_base64: str | None = None

    @property
    def cpf_mascarado(self) -> str | None:
        if not self.dados_pessoa:
            return None
        cpf = self.dados_pessoa.get("cpf") or self.dados_pessoa.get("CPF")
        if not cpf:
            return None
        if "*" in cpf or len(cpf) <= 4:
            return cpf
        return f"{cpf[:3]}.***.***-{cpf[-2:]}"
