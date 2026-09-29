from __future__ import annotations

import re
import unicodedata
from typing import Any

from bs4 import BeautifulSoup

_LABEL_ALIASES = {
    "nome": ["nome", "nome completo"],
    "cpf": ["cpf"],
    "nis": ["nis"],
    "data_nascimento": ["data de nascimento", "nascimento"],
    "beneficiario_social": ["beneficiario de programa social"],
    "status": ["status"],
    "matricula": ["matricula"],
}
BENEFIT_NAMES = ("Auxílio Brasil", "Auxílio Emergencial", "Bolsa Família")


def normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", value)
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).lower().split())


def _text(tag) -> str:
    return " ".join(tag.get_text(" ", strip=True).split())


def _content(html: str):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.select("script, style, nav, header, footer"):
        tag.decompose()
    return soup.select_one("#main-content") or soup.find("main") or soup


def _pairs(root) -> dict[str, str]:
    pairs = {}
    for tag in root.find_all(["dt", "th", "label", "strong", "b", "span", "div", "p"]):
        # Ignore wrappers so that unrelated fields cannot become one value.
        if tag.find(["dt", "th", "label", "strong", "b", "span", "div", "p"]):
            continue
        label = _text(tag)
        if ":" in label:
            label, value = label.split(":", 1)
            if not value.strip():
                sibling = tag.find_next_sibling()
                value = _text(sibling) if sibling else ""
        else:
            sibling = tag.find_next_sibling()
            if sibling is None or sibling.name not in {"dd", "td", "span", "div", "p", "a"}:
                continue
            value = _text(sibling)
        if label.strip() and value.strip():
            pairs[label.strip().rstrip(":")] = value.strip()
    return pairs


def parse_person_data(html: str) -> dict[str, Any]:
    root = _content(html)
    pairs = _pairs(root)
    data: dict[str, Any] = {}
    for label, value in pairs.items():
        for field, aliases in _LABEL_ALIASES.items():
            if normalize(label) in aliases:
                data[field] = value
    # A generic page title must never be accepted as a person's name.
    if "nome" not in data and ("cpf" in data or "nis" in data):
        heading = root.find("h1")
        if heading and not any(word in normalize(_text(heading)) for word in ("panorama", "pessoa fisica", "busca", "portal")):
            data["nome"] = _text(heading)
    if not data.get("nome") or not (data.get("cpf") or data.get("nis")):
        return {}
    if not data.get("nis"):
        identifiers = set()
        for table in root.select("table"):
            headers = [normalize(_text(cell)) for cell in table.select("thead th")]
            if "nis" not in headers:
                continue
            index = headers.index("nis")
            for row in table.select("tbody tr"):
                cells = row.find_all("td", recursive=False)
                if len(cells) > index:
                    identifiers.add(_text(cells[index]))
        if len(identifiers) == 1:
            data["nis"] = identifiers.pop()
    data["campos_adicionais"] = {
        key: value for key, value in pairs.items()
        if not any(normalize(key) in aliases for aliases in _LABEL_ALIASES.values())
    }
    return data


def parse_benefits(html: str) -> list[dict[str, Any]]:
    root = _content(html)
    benefits = []
    seen = set()
    for block in root.select("a[href], .beneficio, .benefit-card, li, tr"):
        if block.name != "a" and block.find("a", href=True):
            continue
        description = _text(block)
        href = block.get("href", "") if block.name == "a" else ""
        for name in BENEFIT_NAMES:
            slug = normalize(name).replace(" ", "-")
            if normalize(name) not in normalize(description) and f"/beneficios/{slug}/" not in (href or ""):
                continue
            link = block if block.name == "a" else block.find("a", href=True)
            href = link.get("href") if link else None
            key = (name, href)
            if key in seen:
                continue
            seen.add(key)
            benefits.append({"tipo": name, "detalhes": {"descricao": description}, "url": href})
    return benefits


def parse_benefit_details(html: str) -> dict[str, Any]:
    root = _content(html)
    tables = []
    for table in root.find_all("table"):
        headers = [_text(cell) for cell in table.select("thead th")]
        rows = []
        for row in table.select("tr"):
            cells = [_text(cell) for cell in row.find_all("td", recursive=False)]
            if row.select_one("td.dataTables_empty"):
                continue
            if cells:
                rows.append(dict(zip(headers, cells)) if len(headers) == len(cells) and len(set(headers)) == len(headers) else cells)
        if rows:
            tables.append({"id": table.get("id"), "colunas": headers, "linhas": rows})
    return {"campos": _pairs(root), "tabelas": tables, "texto": _text(root)}
