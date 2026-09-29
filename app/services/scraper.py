from __future__ import annotations

import asyncio
import re
import uuid
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit

from playwright.async_api import Page, async_playwright

from app.core.config import settings
from app.core.logging import logger
from app.parsers.portal_parser import normalize, parse_benefit_details, parse_benefits, parse_person_data
from app.schemas.consulta import Beneficio, ConsultaRequest, ConsultaResponse
from app.services.browser_pool import BrowserPool
from app.utils.evidence import page_to_base64
from app.utils.errors import DomainError, NoResultsError, PortalBlockedError, SearchTimeoutError, ScrapingValidationError

TIMEOUT_MESSAGE = "Não foi possível retornar os dados no tempo de resposta solicitado"
PERSON_LINKS = "a[href^='/busca/pessoa-fisica/'], a[href^='/pessoa-fisica/']:not([href*='/busca'])"
ZERO_RESULTS = re.compile(r"0 resultados|nenhum resultado|sem resultados", re.I)


class TransparenciaScraper:
    """One isolated browser per consultation; capacity is shared by API requests."""

    def __init__(self, browser_pool: BrowserPool | None = None, portal_url: str | None = None):
        self.browser_pool = browser_pool or BrowserPool(settings.MAX_CONCURRENT_REQUESTS)
        self.portal_url = (portal_url or settings.PORTAL_URL).rstrip("/")

    @staticmethod
    def _build_error_response(termo: str, mensagem: str) -> ConsultaResponse:
        return ConsultaResponse(id_consulta=str(uuid.uuid4()), status="erro", termo=termo, mensagem=mensagem)

    @staticmethod
    def _mask_cpf(raw_value: str | None) -> str | None:
        if not raw_value or "*" in raw_value:
            return raw_value
        digits = re.sub(r"\D", "", raw_value)
        return f"{digits[:3]}.***.***-{digits[-2:]}" if len(digits) == 11 else raw_value

    async def consultar(self, termo: str, filtro_beneficiario_social: bool = False) -> ConsultaResponse:
        payload = ConsultaRequest(termo=termo, filtro_beneficiario_social=filtro_beneficiario_social)
        try:
            # Queueing and navigation share a total deadline.
            async with asyncio.timeout(settings.REQUEST_TIMEOUT_SECONDS):
                return await self.browser_pool.run(lambda: self._run(payload))
        except DomainError:
            raise
        except Exception as exc:
            logger.warning("Falha na automação: %s", type(exc).__name__)
            raise SearchTimeoutError(TIMEOUT_MESSAGE) from exc

    async def _run(self, payload: ConsultaRequest) -> ConsultaResponse:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=settings.PLAYWRIGHT_HEADLESS)
            try:
                context = await browser.new_context(viewport={"width": 1440, "height": 1200}, locale="pt-BR")
                context.set_default_timeout(settings.NAVIGATION_TIMEOUT_MS)
                context.set_default_navigation_timeout(settings.NAVIGATION_TIMEOUT_MS)
                page = await context.new_page()
                await self._goto(page, self.portal_url)
                await self._open_people_search(page)
                await self._search_for_term(page, payload.termo, payload.filtro_beneficiario_social)
                await self._open_first_person(page, payload.termo)
                await self._expand_sections(page)
                # The panorama may render its fields after DOMContentLoaded.
                while True:
                    await self._check_block(page)
                    html = await page.content()
                    person = parse_person_data(html)
                    if person:
                        break
                    await asyncio.sleep(0.1)
                if re.fullmatch(r"[\d.\-\s]+", payload.termo) and not self._matches_identifier(payload.termo, person):
                    raise ScrapingValidationError("CPF/NIS do panorama não corresponde à consulta.")
                person["cpf"] = self._mask_cpf(person.get("cpf"))
                evidence = await page_to_base64(page)
                benefits = await self._collect_benefits(page, html)
                return ConsultaResponse(
                    id_consulta=str(uuid.uuid4()), status="sucesso",
                    data_hora=datetime.now(timezone.utc), termo=payload.termo,
                    dados_pessoa=person, beneficios=benefits, evidencia_base64=evidence,
                )
            finally:
                await browser.close()

    @staticmethod
    def _matches_identifier(term: str, person: dict) -> bool:
        digits = re.sub(r"\D", "", term)
        for field in ("cpf", "nis"):
            value = re.sub(r"[^\d*]", "", person.get(field, ""))
            if len(value) == len(digits) and any(c.isdigit() for c in value):
                if all(actual == "*" or actual == expected for actual, expected in zip(value, digits)):
                    return True
        return False

    def _portal_link(self, current_url: str, href: str) -> str:
        target = urljoin(current_url, href)
        if urlsplit(target).scheme not in {"http", "https"} or urlsplit(target).netloc != urlsplit(self.portal_url).netloc:
            raise ScrapingValidationError("Link de navegação fora do portal.")
        return target

    async def _goto(self, page: Page, url: str) -> None:
        response = await page.goto(url, wait_until="domcontentloaded")
        await self._check_block(page)
        if response and response.status >= 400:
            raise SearchTimeoutError(TIMEOUT_MESSAGE)

    async def _check_block(self, page: Page) -> None:
        title = normalize(await page.title())
        if "human verification" in title or "verificacao humana" in title:
            raise PortalBlockedError("Verificação humana exigida pelo portal.")
        if await page.locator("#captcha-container:visible, iframe[src*='captcha'][src*='/bframe']:visible").count():
            raise PortalBlockedError("CAPTCHA detectado pelo portal.")

    async def _expand_sections(self, page: Page) -> None:
        for button in await page.locator("#main-content .br-accordion button.header[aria-controls]").all():
            target_id = await button.get_attribute("aria-controls")
            target = page.locator(f'[id="{target_id}"]')
            if await target.count() and not await target.is_visible():
                await button.click()
                await target.wait_for(state="visible")

    async def _open_people_search(self, page: Page) -> None:
        link = page.get_by_role("link", name=re.compile(r"pessoas? f[ií]sicas?", re.I)).first
        if await link.count() and await link.is_visible():
            href = await link.get_attribute("href")
            if href:
                await self._goto(page, self._portal_link(page.url, href))
            else:
                await self._goto(page, self.portal_url + "/pessoa/visao-geral")
        else:
            await self._goto(page, self.portal_url + "/pessoa/visao-geral")
        physical = page.locator("a[href='/pessoa-fisica/busca/lista']").first
        if await physical.count():
            await self._goto(page, self.portal_url + "/pessoa-fisica/busca/lista")

    async def _search_for_term(self, page: Page, termo: str, filtro_beneficiario_social: bool) -> None:
        field = page.locator(
            "input[name*='termo' i]:visible, input[name*='nome' i]:visible, "
            "input[name*='cpf' i]:visible, input[name*='nis' i]:visible, "
            "input[placeholder*='nome' i]:visible, input[placeholder*='cpf' i]:visible, "
            "input[placeholder*='nis' i]:visible"
        ).first
        await field.fill(termo)
        if filtro_beneficiario_social:
            social = page.get_by_label(re.compile(r"benefici[aá]rio de programa social", re.I)).first
            if not await social.is_visible():
                await page.get_by_role("button", name=re.compile("refine a busca", re.I)).click()
            await social.check()
        # Scope the submit to this input's form, excluding the global header search.
        form = field.locator("xpath=ancestor::form")
        submit = form.get_by_role("button", name=re.compile(r"enviar dados do formulário de busca|^buscar$|^pesquisar$|^consultar$", re.I)).first
        if await submit.count():
            await submit.click()
        else:
            await field.press("Enter")
        if await page.locator("#form-superior").count():
            await page.wait_for_url(re.compile(r"[?&]termo="))
            await page.locator("#resultados").wait_for(state="attached")

    async def _open_first_person(self, page: Page, termo: str) -> None:
        # Wait for observable results, not networkidle (analytics can keep it busy).
        results = page.locator(PERSON_LINKS).filter(visible=True)
        zero = page.get_by_text(ZERO_RESULTS).first
        while True:
            await self._check_block(page)
            if await zero.count() and await zero.is_visible():
                if re.fullmatch(r"[\d.\-\s]+", termo):
                    raise SearchTimeoutError(TIMEOUT_MESSAGE)
                raise NoResultsError(f"Foram encontrados 0 resultados para o termo {termo}")
            if await results.count():
                break
            await asyncio.sleep(0.1)
        numeric = re.fullmatch(r"[\d.\-\s]+", termo) is not None
        for link in await results.all():
            label = normalize(await link.inner_text())
            if not numeric and not all(word in label.split() for word in normalize(termo).split()):
                continue
            href = await link.get_attribute("href")
            if href:
                await self._goto(page, self._portal_link(page.url, href))
                return
        if numeric:
            raise SearchTimeoutError(TIMEOUT_MESSAGE)
        raise NoResultsError(f"Foram encontrados 0 resultados para o termo {termo}")

    async def _collect_benefits(self, page: Page, html: str) -> list[Beneficio]:
        panorama_url = page.url
        benefits = []
        for item in parse_benefits(html):
            href = item.pop("url")
            if not href or href.startswith("#"):
                raise ScrapingValidationError("Benefício sem link de detalhes acessível.")
            url = self._portal_link(panorama_url, href)
            await self._goto(page, url)
            await self._expand_sections(page)
            details = {"url": url, "paginas": []}
            data_tables = page.locator("#main-content table[id]")
            if await data_tables.count():
                # Each DataTable has its own cursor, including initially collapsed tables.
                for table in await data_tables.all():
                    table_id = await table.get_attribute("id")
                    seen = set()
                    while True:
                        await table.locator("tbody td").first.wait_for(state="visible")
                        processing = page.locator(f'[id="{table_id}_processing"]')
                        if await processing.count():
                            await processing.wait_for(state="hidden")
                        signature = await table.locator("tbody").inner_text()
                        if signature in seen:
                            raise ScrapingValidationError("Paginação de benefício não avançou.")
                        seen.add(signature)
                        parsed = parse_benefit_details(await table.evaluate("el => el.outerHTML"))
                        details["paginas"].append({"tabela_id": table_id, **parsed})
                        next_page = page.locator(f'[id="{table_id}_next"]')
                        if not await next_page.count():
                            break
                        if await next_page.evaluate("el => el.classList.contains('disabled')"):
                            break
                        await next_page.locator("button, a").click()
                        await page.wait_for_function(
                            "({id, previous}) => document.getElementById(id)?.querySelector('tbody')?.innerText !== previous",
                            arg={"id": table_id, "previous": signature},
                        )
                        await self._check_block(page)
            else:
                seen = set()
                while True:
                    table = page.locator("main table, table").first
                    await table.locator("td").first.wait_for(state="visible")
                    signature = await table.inner_text()
                    if signature in seen:
                        raise ScrapingValidationError("Paginação de benefício não avançou.")
                    seen.add(signature)
                    details["paginas"].append(parse_benefit_details(await page.content()))
                    next_page = page.get_by_role("link", name=re.compile(r"pr[oó]xim[oa]|seguinte|next", re.I)).or_(
                        page.get_by_role("button", name=re.compile(r"pr[oó]xim[oa]|seguinte|next", re.I))
                    ).first
                    if not await next_page.count() or not await next_page.is_visible():
                        break
                    disabled = await next_page.evaluate("el => !!el.closest('.disabled, [aria-disabled=\"true\"]') || el.disabled === true")
                    if disabled:
                        break
                    await next_page.click()
                    await page.wait_for_function(
                        "previous => document.querySelector('table')?.innerText !== previous", arg=signature
                    )
                    await self._check_block(page)
            details["campos"] = parse_benefit_details(await page.content())["campos"]
            item["detalhes"].update(details)
            benefits.append(Beneficio.model_validate(item))
        return benefits
