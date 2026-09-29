"""Synthetic HTML exercises the browser; it does not certify the live portal DOM."""

import asyncio
import base64
import html
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import pytest

from app.core.config import settings
from app.services.browser_pool import BrowserPool
from app.services.scraper import TIMEOUT_MESSAGE, TransparenciaScraper
from app.utils.errors import NoResultsError, PortalBlockedError, SearchTimeoutError

pytestmark = pytest.mark.browser


@pytest.fixture
def portal(monkeypatch):
    visited = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            visited.append(self.path)
            url = urlsplit(self.path)
            query = parse_qs(url.query)
            if url.path == "/":
                body = '<a href="/pessoa/visao-geral">Pessoas Físicas e Jurídicas</a>'
            elif url.path == "/pessoa/visao-geral":
                body = '<a href="/pessoa-fisica/busca/lista">Busca de Pessoa Física</a>'
            elif url.path == "/blocked":
                body = '<title>Human Verification</title><div id="captcha-container"></div>'
            elif url.path == "/pessoa-fisica/busca/lista":
                body = '''<header><form action="/wrong"><input name="global"><button>Pesquisar</button></form></header>
                <form action="/resultados"><input name="termo" placeholder="Nome, CPF ou NIS">
                <label><input type="checkbox" name="outro">Outro filtro</label>
                <button type="button" onclick="document.getElementById('filters').hidden=false">Refine a Busca</button>
                <div id="filters" hidden><label><input type="checkbox" name="social">BENEFICIÁRIO DE PROGRAMA SOCIAL</label></div>
                <button>Buscar</button></form>'''
            elif url.path == "/resultados":
                term = query["termo"][0]
                if term in {"Nome inexistente", "99999999999", "999.999.999-99"}:
                    body = '<p>Foram encontrados 0 resultados</p>'
                else:
                    body = '''<main id="results">Carregando</main><script>
                    setTimeout(() => document.getElementById('results').innerHTML = '<a href="/busca/pessoa-fisica/1">Maria da Silva</a><a href="/busca/pessoa-fisica/2">Maria da Silva</a>', 150);
                    </script>'''
            elif url.path.startswith("/busca/pessoa-fisica/"):
                body = '''<main><h1>Pessoa Física - Panorama</h1><dl><dt>Nome</dt><dd>Maria da Silva</dd>
                <dt>CPF</dt><dd>***.123.456-**</dd><dt>NIS</dt><dd>12345678901</dd>
                <dt>Município</dt><dd>Recife</dd></dl><ul>'''
                for i, name in enumerate(("Auxílio Brasil", "Auxílio Emergencial", "Bolsa Família")):
                    body += f'<li><a href="/beneficio/{i}">{name}</a></li>'
                body += '</ul></main>'
            elif url.path == "/multiple-tables":
                body = '<main><div id="main-content"><div class="br-accordion">'
                for index in range(2):
                    body += f'''<button class="header" aria-controls="section{index}" onclick="document.getElementById('section{index}').hidden=false">Recursos {index}</button>
                    <div id="section{index}" hidden><table id="table{index}"><thead><tr><th>Mês</th></tr></thead>
                    <tbody><tr><td>01/2026</td></tr></tbody></table>
                    <ul><li id="table{index}_next"><button onclick="setTimeout(() => {{document.querySelector('#table{index} tbody').innerHTML='<tr><td>02/2026</td></tr>'; document.getElementById('table{index}_next').classList.add('disabled');}}, 100)"> &gt; </button></li></ul></div>'''
                body += '</div><iframe src="/recaptcha/api2/anchor"></iframe></div></main>'
            elif url.path.startswith("/beneficio/"):
                month = "02/2026" if query else "01/2026"
                body = f'<main><h1>Detalhes do benefício {html.escape(url.path)}</h1><table><thead><tr><th>Mês</th><th>Valor</th></tr></thead><tbody><tr><td>{month}</td><td>R$ 600,00</td></tr></tbody></table>'
                body += '<button disabled>Próxima</button>' if query else '<a href="?pagina=2">Próxima</a>'
                body += '</main>'
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode())

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(settings, "REQUEST_TIMEOUT_SECONDS", 20)
    monkeypatch.setattr(settings, "NAVIGATION_TIMEOUT_MS", 3000)
    yield f"http://127.0.0.1:{server.server_port}", visited
    server.shutdown()
    server.server_close()
    thread.join()


@pytest.mark.parametrize("termo,social", [("12345678901", False), ("Maria da Silva", False), ("Silva", True)])
async def test_browser_success(portal, termo, social):
    url, visited = portal
    result = await TransparenciaScraper(portal_url=url).consultar(termo, social)
    assert result.status == "sucesso"
    assert result.dados_pessoa["nome"] == "Maria da Silva"
    assert result.dados_pessoa["cpf"] == "***.123.456-**"
    assert result.dados_pessoa["campos_adicionais"]["Município"] == "Recife"
    assert base64.b64decode(result.evidencia_base64).startswith(b"\x89PNG\r\n\x1a\n")
    assert len(result.beneficios) == 3
    assert result.beneficios[0].detalhes["paginas"][1]["tabelas"][0]["linhas"][0]["Mês"] == "02/2026"
    assert "/busca/pessoa-fisica/2" not in visited
    requests = [p for p in visited if p.startswith("/resultados?")]
    assert ("social=on" in requests[0]) == social
    assert "outro=on" not in requests[0]


@pytest.mark.parametrize("termo,error", [("Nome inexistente", NoResultsError), ("99999999999", SearchTimeoutError), ("999.999.999-99", SearchTimeoutError)])
async def test_browser_no_results(portal, termo, error):
    url, _ = portal
    with pytest.raises(error) as exc:
        await TransparenciaScraper(portal_url=url).consultar(termo)
    assert str(exc.value) == (f"Foram encontrados 0 resultados para o termo {termo}" if error is NoResultsError else TIMEOUT_MESSAGE)


async def test_browser_block(portal):
    url, _ = portal
    with pytest.raises(PortalBlockedError):
        await TransparenciaScraper(portal_url=url + "/blocked").consultar("Maria")


async def test_simultaneous_browsers(portal):
    url, _ = portal
    scraper = TransparenciaScraper(BrowserPool(2), portal_url=url)
    results = await asyncio.gather(scraper.consultar("Maria"), scraper.consultar("Silva", True))
    assert all(result.status == "sucesso" for result in results)
    assert results[0].id_consulta != results[1].id_consulta


async def test_independent_tables_and_nonblocking_recaptcha(portal):
    from playwright.async_api import async_playwright

    url, _ = portal
    scraper = TransparenciaScraper(portal_url=url)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        try:
            page = await browser.new_page()
            await page.goto(url)
            benefits = await scraper._collect_benefits(page, '<main><a href="/multiple-tables">Bolsa Família</a></main>')
            pages = benefits[0].detalhes["paginas"]
            assert [p["tabela_id"] for p in pages] == ["table0", "table0", "table1", "table1"]
            assert [p["tabelas"][0]["linhas"][0]["Mês"] for p in pages] == ["01/2026", "02/2026"] * 2
        finally:
            await browser.close()
