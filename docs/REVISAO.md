# Revisão de código e aderência

Referência: [desafio-01](https://github.com/mostqi/desafios-fullstack-python/tree/main/desafio-01), consultado em 29/09/2026. Esta revisão alterou os arquivos locais; a pasta `.git` disponível estava vazia e não foi possível obter histórico ou gerar um diff Git.

## Achados por gravidade

| Prioridade | Problema observado antes da revisão | Correção / estado |
| --- | --- | --- |
| P1 | `app/services/scraper.py` extraía HTML imediatamente após pesquisar, sem abrir uma pessoa | Adicionada seleção do primeiro resultado equivalente e abertura do panorama |
| P1 | `app/parsers/portal_parser.py` aceitava título de qualquer página como nome | Removido sucesso por título; exigidos nome e CPF/NIS reconhecidos |
| P1 | Benefícios eram apenas textos do panorama, sem acessar detalhes | Navegação pelos links, extração de tabelas/texto e paginação; componentes diferentes ainda exigem validação real |
| P1 | Filtro social marcava o primeiro checkbox/radio e ignorava falhas | Seleção pelo rótulo do filtro; falhas não são ocultadas |
| P1 | `workflows/n8n_workflow.json` não tinha gatilho e usava operação/parâmetros inadequados para arquivo no Drive | Webhook, preparação binária e operação upload configurados; execução externa pendente |
| P1 | Sheets tentava ler pessoa e ID no JSON de metadados devolvido pelo Drive | Referências explícitas ao nó HTTP; operação append e URL por ID do arquivo |
| P2 | CPF/NIS sem resultado recebia mensagem destinada a nomes | Mapeamento corrigido conforme o tipo de termo |
| P2 | `termo` só com espaços passava pela validação | Normalização antes de validar comprimento |
| P2 | Capacidade zero travava a fila e não havia prazo total | Configuração positiva e timeout incluindo fila |
| P2 | Falha em `new_context` ocorria fora do finally de fechamento | Criação de contexto protegida pelo finally do navegador |
| P2 | CPF previamente mascarado era remontado com dígitos em posições incorretas | Máscara existente preservada; identificador consultado conferido quando possível |
| P2 | CLI imprimia traceback para falhas de domínio | JSON de erro e código de saída 1 |
| P2 | Docker copiava `.env` e `.venv`; Compose usava booleano de ambiente sem aspas | `.dockerignore` e variável como string; comando respeita PORT |
| P2 | Testes HTTP substituíam toda a automação | Adicionados testes Chromium locais, de fila, parser e limpeza |
| P3 | Dependências sem limite superior e LOG_LEVEL ignorado | Versões diretas fixadas nas instaladas e logging conectado à configuração |

## Evidências e limites

- Resultado final: **31 testes passaram** com Python 3.14 e Playwright 1.63.0. `pip check` não encontrou dependências incompatíveis e `compileall` validou a sintaxe de `app` e `tests`.
- Os dez testes originais passaram antes das alterações. Isso evidenciou uma lacuna de cobertura, não uma garantia de funcionamento do robô.
- A suíte ampliada usa Chromium headless e um servidor HTTP sintético temporário. Nenhuma consulta real de pessoa é necessária nesses testes.
- Foi verificada a resposta pública Human Verification / AWS WAF com uma requisição à rota de busca. O corpo retornado não continha o formulário esperado.
- Os formatos do workflow foram conferidos com o código oficial dos nós [Drive v1](https://github.com/n8n-io/n8n/blob/master/packages/nodes-base/nodes/Google/Drive/v1/GoogleDriveV1.node.ts) e [Sheets append](https://github.com/n8n-io/n8n/blob/master/packages/nodes-base/nodes/Google/Sheet/v2/actions/sheet/append.operation.ts). Conferência estática não equivale a execução no n8n.
- Docker não está disponível nesta máquina; a imagem não foi construída na revisão.
- O ambiente de testes emite aviso de depreciação de Starlette sobre o transporte HTTPX do TestClient. Os testes passam; a migração do transporte é uma manutenção futura, não um erro de consulta demonstrado.

## Pendências que impedem afirmar conformidade completa

1. **P1: homologação do portal real.** Os seletores são hipóteses conservadoras verificadas no portal sintético, não seletores certificados do HTML de produção. Acesso legítimo sem o bloqueio é necessário para completar essa etapa. Verificar especialmente rótulos, links de resultados, campos do panorama, carregamento AJAX, detalhes e paginação.
2. **P1 para o bônus: publicação online e Google.** Importar o workflow na versão de n8n escolhida, configurar OAuth, conferir arquivo e linha reais e fornecer URL acessível da API.
3. **P2: operação pública.** Não há autenticação, limite global entre processos, rate limiting nem persistência de tarefas. A máscara do campo CPF não remove dados pessoais do screenshot, termo, NIS ou detalhes.
4. **P2: coleta de layouts não previstos.** Benefícios em abas/modais e tabelas sem os controles suportados ainda precisam de adaptação. Não existe garantia de extrair todos os campos possíveis.

## Roteiro de aceitação final

Execute os cenários do enunciado em ambiente autorizado e compare a resposta com a tela. Para cada sucesso, decodifique o PNG e confira nome/identificador, benefício e todas as páginas disponíveis. Demonstre duas consultas simultâneas. No bônus, baixe o JSON do Drive, compare o ID com o Sheets e abra o link usando a conta autorizada. Só então marque a Parte 2 como entregue.
