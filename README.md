# Portal da Transparência Bot API

Projeto Python para o [desafio-01 da mostQI](https://github.com/mostqi/desafios-fullstack-python/tree/main/desafio-01), com Playwright, FastAPI e um workflow n8n para o bônus.

## Estado da entrega

O fluxo está implementado e coberto por testes de unidade, API e navegador contra um **portal local sintético**. Isso não comprova compatibilidade com o HTML atual do portal público.

Na revisão de 29/09/2026, o portal respondeu com **Human Verification / AWS WAF**. Não foi possível validar os seletores de produção nem concluir uma consulta real. Não há tentativa de contornar CAPTCHA. O robô retorna erro, sem apresentar dados inventados.

O workflow foi corrigido por inspeção do formato dos nós. Importação no n8n, OAuth Google, upload e registro reais ainda precisam de validação. A API não foi publicada online nesta revisão. Portanto, a Parte 2 ainda não deve ser apresentada como concluída.

- [Relatório técnico e dificuldades para iniciantes](RELATORIO.md)
- [Revisão, correções e pendências](docs/REVISAO.md)
- [Configuração do bônus](docs/WORKFLOW.md)
- [Roteiro da apresentação](docs/roteiro_apresentacao.md)

## Requisitos e implementação

| Item do desafio | Implementação | Verificação |
| --- | --- | --- |
| Nome, CPF ou NIS e filtro social opcional | Modelo de entrada e formulário | API e Chromium local |
| Primeiro resultado equivalente e panorama | Navegação e validação de identidade | Chromium local; portal real pendente |
| Evidência Base64 | PNG da página de panorama | Assinatura PNG verificada |
| Detalhes dos três programas | Links e tabelas, com paginação | Chromium local; seletores reais pendentes |
| Headless e simultaneidade | Navegador/contexto por consulta e semáforo | Duas consultas paralelas locais |
| JSON e erros esperados | API e CLI | Testes automatizados |
| Drive e Sheets | Workflow n8n configurável | Integração externa pendente |
| API online para o bônus | Dockerfile e instruções | Publicação pendente |

## Tecnologias e arquitetura

- **Python**: linguagem pedida pelo desafio; permite combinar automação, HTTP e transformação de dados.
- **Playwright**: opção recomendada no enunciado. Controla Chromium headless, oferece localizadores e captura de tela. Cada consulta cria seu próprio navegador e contexto, simplificando o isolamento, ao custo de memória e inicialização.
- **FastAPI + Pydantic**: contrato de entrada/saída, validação e documentação OpenAPI. Permitem demonstrar o robô por HTTP sem acoplar a navegação às rotas.
- **asyncio**: coordena operações de I/O e limita a concorrência. Não torna parsing intensivo em CPU paralelo.
- **BeautifulSoup**: transforma o HTML já renderizado em dados; funções de parsing podem ser testadas sem navegador.
- **pytest + pytest-asyncio + HTTPX**: verificam contratos, erros, concorrência e regressões. Testes de navegador usam Chromium real.
- **Docker**: descreve a instalação do Python, Chromium e bibliotecas do sistema.
- **n8n**: preservado da implementação original, com workflow exportável e nós Google. A justificativa e os custos operacionais estão no relatório.

Fluxo:

```text
POST /consulta ou CLI
  -> validação de entrada
  -> prazo total + semáforo
  -> Chromium/contexto isolado
  -> pesquisa -> primeiro resultado -> panorama -> screenshot
  -> detalhes e páginas dos benefícios
  -> JSON
  -> fechamento do navegador, inclusive em falhas
```

A API compartilha um semáforo por processo. Cinco workers com limite cinco permitem até 25 navegadores, não cinco no total. O CLI tem seu próprio limite; várias invocações não compartilham o semáforo.

## Estrutura

```text
app/
  api/routes.py               # contrato HTTP e erros
  core/config.py              # ambiente e limites
  core/logging.py             # identificador de requisição
  schemas/consulta.py         # entrada e saída
  services/browser_pool.py    # limite por processo
  services/scraper.py         # navegação e coleta
  parsers/portal_parser.py    # interpretação do HTML
  utils/evidence.py           # PNG em Base64
  utils/errors.py             # exceções de domínio
  cli.py                     # execução sem servidor HTTP
tests/                       # unidade, API e Chromium local
workflows/n8n_workflow.json
docs/
```

## Instalação

Python 3.11 ou superior é necessário para `asyncio.timeout`. A revisão executou os testes com Python 3.14; a imagem Docker usa Python 3.12 e ainda precisa de build neste ambiente.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install --with-deps chromium
cp .env.example .env
```

A instalação das dependências do sistema pode solicitar privilégios administrativos. As versões diretas estão fixadas no conjunto instalado durante a revisão; dependências transitivas ainda não têm lock completo.

## Configuração

| Variável | Padrão | Uso |
| --- | --- | --- |
| APP_NAME | transparencia-bot | Nome da API |
| PORT | 8000 | Porta ao executar `python -m app.main` |
| PLAYWRIGHT_HEADLESS | true | Chromium sem janela |
| MAX_CONCURRENT_REQUESTS | 5 | Consultas ativas por processo; mínimo 1 |
| REQUEST_TIMEOUT_SECONDS | 120 | Prazo incluindo espera por vaga |
| NAVIGATION_TIMEOUT_MS | 30000 | Limite de ações/navegação |
| PORTAL_URL | https://portaldatransparencia.gov.br | Origem do portal |
| LOG_LEVEL | INFO | Nível de log |

O prazo total cancela o trabalho; o fechamento do navegador pode acrescentar algum tempo de limpeza. Não há retry automático nem fila persistente.

## API e CLI

```bash
source .venv/bin/activate
python -m app.main
```

- Swagger: [localhost:8000/docs](http://localhost:8000/docs)
- OpenAPI: [localhost:8000/openapi.json](http://localhost:8000/openapi.json)
- Health: [localhost:8000/health](http://localhost:8000/health)

`/health` confirma que a API responde; não verifica acesso ao portal.

```bash
curl -X POST http://localhost:8000/consulta \
  -H 'Content-Type: application/json' \
  -d '{"termo":"Maria da Silva","filtro_beneficiario_social":false}'

python -m app.cli --termo "Silva" --filtro-social
```

O CLI imprime somente o JSON em stdout e retorna código 1 para falhas de consulta. Logs vão para stderr. Para guardar uma execução:

```bash
python -m app.cli --termo "Maria da Silva" > resultado.json
```

Nome e identificadores são strings. CPF com pontuação é aceito; não se valida dígito verificador para evitar rejeitar NIS como se fosse CPF. Campos extras e termos vazios ou só com espaços são rejeitados com HTTP 422.

Resposta de sucesso: `id_consulta` (UUID), `status`, `data_hora` (UTC), `termo`, `dados_pessoa`, `beneficios` e `evidencia_base64`. Os dados incluem campos adicionais reconhecidos por rótulos. Cada benefício contém descrição, URL e `paginas`, com campos, tabelas e texto coletados. Dados ausentes não são inventados.

Falhas de domínio retornam HTTP 200 com `status: "erro"`; isso mantém o contrato original, mas exige que os consumidores inspecionem o JSON. CPF/NIS sem resultado e timeout usam a mensagem de tempo de resposta do enunciado. Nome sem resultado usa a mensagem de zero resultados. Falha em detalhes de benefício invalida a consulta inteira, evitando um sucesso parcial silencioso.

O CPF já mascarado pelo portal é preservado. CPF completo é mascarado no campo estruturado. **Isso não anonimiza o JSON inteiro**: termo, NIS, texto dos detalhes e screenshot podem conter dados pessoais.

## Testes

```bash
python -m pytest -q
python -m pytest -m "not browser" -q
python -m pytest -m browser -q
```

Os testes de navegador sobem um servidor local temporário e não consultam pessoas reais. Cobrem filtro, primeiro resultado, detalhes/paginação, PNG, bloqueio, erros e concorrência. Fixtures artificiais verificam a lógica, não os seletores reais do governo.

Para demonstrar simultaneidade na API, com termos autorizados para a demonstração:

```bash
curl -sS http://localhost:8000/consulta -H 'Content-Type: application/json' -d '{"termo":"Maria da Silva"}' > consulta-1.json &
curl -sS http://localhost:8000/consulta -H 'Content-Type: application/json' -d '{"termo":"Silva","filtro_beneficiario_social":true}' > consulta-2.json &
wait
```

Confira os dois UUIDs, os status e as evidências. Arquivos de erro não demonstram uma coleta bem-sucedida.

## Docker e publicação

```bash
docker compose up --build
```

A configuração publica a porta 8000. O `.dockerignore` exclui ambiente virtual, segredos e caches do contexto de build. O comando da imagem respeita `PORT`. Ajuste também o mapeamento de portas se alterar essa variável no Compose.

Para a entrega online do bônus, publique a imagem em um ambiente que suporte Chromium e tenha memória para o limite escolhido; configure HTTPS, controle de acesso e limites antes de expor a automação. Registre a URL em sua entrega e teste a partir de outra máquina. Nenhum provedor foi provisionado nesta revisão.

## Limites conhecidos

- O layout real, resultados carregados por AJAX e seletores de detalhes ainda precisam de conferência após o bloqueio do portal ser resolvido legitimamente.
- A paginação suporta controles visíveis “Próxima/Próximo”, “Seguinte” ou “Next”. Links sem URL, modais, abas e outros componentes precisam de adaptação.
- O parser exige nome e CPF/NIS identificáveis. Páginas com estrutura diferente retornam erro; não há promessa de cobertura de todos os campos possíveis.
- A API não tem autenticação, rate limiting, armazenamento persistente ou idempotência.
- Não publique JSONs, screenshots ou credenciais no Git. O n8n também pode guardar esses dados no histórico de execução.
