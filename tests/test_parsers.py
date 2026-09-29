from pathlib import Path

from app.parsers.portal_parser import parse_benefits, parse_person_data
from app.services.scraper import TransparenciaScraper

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "person_page.html"


def test_parse_person_data():
    html = FIXTURE_PATH.read_text(encoding="utf-8")
    parsed = parse_person_data(html)

    assert parsed["nome"] == "Maria da Silva"
    assert parsed["cpf"] == "123.456.789-09"
    assert parsed["nis"] == "12345678901"


def test_parse_benefits():
    html = FIXTURE_PATH.read_text(encoding="utf-8")
    benefits = parse_benefits(html)

    assert len(benefits) >= 3
    assert {item["tipo"] for item in benefits}.issuperset({"Auxílio Brasil", "Bolsa Família", "Auxílio Emergencial"})


def test_generic_page_is_not_a_person():
    assert parse_person_data("<title>Human Verification</title><h1>Portal</h1>") == {}
    assert parse_person_data("<h1>Busca</h1><label>Nome</label><input name='nome'>") == {}


def test_wrappers_do_not_mix_fields():
    html = "<main><div><div><span>Nome:</span><span>Maria da Silva</span></div><div><span>CPF:</span><span>***.123.456-**</span></div></div></main>"
    person = parse_person_data(html)
    assert person["nome"] == "Maria da Silva"
    assert person["cpf"] == "***.123.456-**"
    assert TransparenciaScraper._mask_cpf(person["cpf"]) == person["cpf"]


def test_menu_is_not_a_benefit_and_links_are_unique():
    html = '<nav><a href="/menu">Bolsa Família</a></nav><main><li><a href="/detalhes">Auxílio Brasil</a></li></main>'
    benefits = parse_benefits(html)
    assert len(benefits) == 1
    assert benefits[0]["url"] == "/detalhes"


def test_identifiers_must_match_without_destroying_mask():
    assert TransparenciaScraper._matches_identifier("123.456.789-09", {"cpf": "***.456.789-**"})
    assert not TransparenciaScraper._matches_identifier("99999999999", {"cpf": "***.456.789-**"})
    assert not TransparenciaScraper._matches_identifier("99999999999", {"cpf": "***.***.***-**"})


def test_observed_panorama_structure_without_personal_data():
    html = '''<main><header>Menu</header><div id="main-content">
    <section class="dados-tabelados"><div><strong>Nome</strong><span>Pessoa de Teste</span></div>
    <div><strong>CPF</strong><span>***.123.456-**</span></div></section>
    <div class="responsive"><strong>Auxílio Emergencial</strong><br><table>
    <thead><tr><th>Detalhar</th><th>NIS</th><th>Nome</th></tr></thead>
    <tbody><tr><td><a href="/beneficios/auxilio-emergencial/1">Detalhar</a></td>
    <td>1.234.567.890-1</td><td>Pessoa de Teste</td></tr></tbody></table></div></div></main>'''
    assert parse_person_data(html)["nis"] == "1.234.567.890-1"
    benefits = parse_benefits(html)
    assert len(benefits) == 1
    assert benefits[0]["tipo"] == "Auxílio Emergencial"
    assert benefits[0]["url"] == "/beneficios/auxilio-emergencial/1"
