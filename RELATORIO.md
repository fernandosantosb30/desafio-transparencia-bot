# Relatório técnico

## Objetivo e situação comprovada

A implementação foi revisada contra o [desafio-01](https://github.com/mostqi/desafios-fullstack-python/tree/main/desafio-01). A revisão corrigiu navegação incompleta, extração permissiva, validação, erros, isolamento e o formato do workflow.

Há testes com Chromium real sobre um portal sintético. Na tentativa de acesso público em 29/09/2026, foi recebida uma página Human Verification do AWS WAF. Assim, não foi comprovado sucesso no portal real. Google Drive/Sheets e publicação online também permanecem pendentes.

Este relatório descreve o código e os problemas observados na revisão. Não é um depoimento sobre a experiência pessoal do autor original; adapte a apresentação oral apenas ao que você realmente executou e compreendeu.

## Por que estas tecnologias

| Tecnologia | Motivo no projeto | Custo ou alternativa |
| --- | --- | --- |
| Python | Requisito e ecossistema de automação | Exige organizar exceções e tarefas assíncronas |
| Playwright/Chromium | Recomendação do desafio, interação com páginas renderizadas e screenshots | Consome mais memória que HTTP direto; seletores dependem do DOM |
| FastAPI | API pequena, funções async e Swagger gerado do contrato | Não resolve autenticação, filas ou disponibilidade sozinho |
| Pydantic/Settings | Validação e configuração centralizadas | Validação deve ocorrer na ordem correta: limpar espaços antes de medir tamanho |
| BeautifulSoup | Parsing separado do navegador, simples de testar com HTML | Não executa JavaScript; depende do HTML entregue pelo Playwright |
| asyncio | Sobrepõe esperas e controla o número de consultas | Estado compartilhado e cancelamento exigem cuidado |
| pytest/HTTPX | Regressões e contrato HTTP verificáveis | Mocks isolados não demonstram navegação real |
| Docker | Instalação documentada do navegador e dependências | Build e execução ainda precisam ser testados onde Docker estiver disponível |
| n8n | Workflow visual exportável, HTTP e integração Google | Credenciais, hospedagem e versões de nós precisam ser mantidas |

Manter Playwright segue o enunciado. Não é necessário afirmar que Selenium seria incapaz de isolamento ou headless. A decisão se apoia na adequação da API assíncrona e no requisito concreto desta solução.

Um navegador por consulta facilita encerramento e isolamento de cookies. Reutilizar um navegador com vários contextos poderia reduzir custo de inicialização, mas exigiria gerenciamento de ciclo de vida compartilhado. Para este porte, a opção atual é mais fácil de inspecionar.

Não foi adicionado banco de dados: a saída principal é um documento JSON e o bônus delega o arquivo ao Drive e o índice ao Sheets. Uma fila/banco seria útil para trabalhos demorados, recuperação e idempotência, mas adicionaria operações que esta versão não implementa.

## Por que n8n no bônus

O projeto já usava n8n, então foi preservado. As plataformas do enunciado são sugestões; o importante é demonstrar a orquestração e o armazenamento solicitado.

A opção se justifica pelo editor visual, exportação JSON e integração via OAuth. Isso permite discutir o fluxo sem misturar credenciais ao código Python. A edição self-hosted envolve administração e infraestrutura; não se deve apresentar o serviço cloud como permanentemente gratuito. Consulte o [projeto oficial](https://github.com/n8n-io/n8n) antes de escolher a hospedagem.

O fluxo revisado recebe um webhook, chama a API, prepara um binário JSON, faz upload e adiciona uma linha. A resposta do Drive contém metadados do arquivo; por isso, os dados da pessoa no Sheets vêm explicitamente do nó HTTP Request.

## Partes mais difíceis para um iniciante

### 1. Entender estados de uma página dinâmica

Digitar no formulário não significa que o panorama já está aberto. Há estados diferentes: pesquisa, carregamento, lista, zero resultados, pessoa selecionada e detalhes. No código anterior faltava a transição da lista para a pessoa. O parser recebia a página errada.

O aprendizado mais importante é inspecionar o DOM em cada etapa, definir qual elemento confirma a transição e só então extrair dados. Esperar um número fixo de segundos ou apenas ausência de tráfego não prova que a página correta carregou.

### 2. Separar dado verdadeiro de texto parecido

O parser anterior podia usar o título de uma página de erro como nome. Também encontrava CPF dentro de contêineres extensos e tratava menções em menus como benefícios.

A solução exige rótulos reconhecidos, identidade mínima, exclusão de áreas de navegação e testes de páginas negativas. Retornar erro quando não há evidência suficiente é melhor para a qualidade dos dados do que fabricar um sucesso. Campos extras são preservados quando o parser os reconhece; cobertura total do portal segue pendente.

### 3. Concorrência, limpeza e limite de tempo

Uma função async não garante isolamento. É preciso saber quem compartilha o semáforo, quem cria o navegador e quem o encerra quando ocorre exceção ou cancelamento. Um limite zero antes deixava tarefas esperando indefinidamente.

Agora a capacidade é positiva, o prazo inclui a espera na fila e o navegador é fechado em finally. O teste de concorrência verifica o limite; o teste de navegador executa duas consultas simultâneas. Vários processos continuam tendo limites independentes.

### 4. Extrair detalhes sem perder o contexto da consulta

Cada programa tem sua própria página; uma descrição no panorama não substitui a coleta de detalhes. Também é necessário seguir as páginas da tabela e reconhecer o fim.

O código captura a evidência no panorama antes de navegar pelos benefícios. Preserva URLs, campos, linhas e texto das páginas. Se um benefício não tiver link suportado, a consulta falha, em vez de dizer que a coleta ficou completa.

### 5. Integrar sistemas com formatos diferentes

No n8n, um nó pode substituir completamente o JSON de entrada. Este era o erro entre Drive e Sheets. Além disso, upload de arquivo exige conteúdo binário e parâmetros compatíveis com a versão do nó.

Para um iniciante, vale testar cada etapa com dados fictícios, inspecionar entrada/saída e depois conferir o arquivo baixado e a linha gravada. OAuth e permissões não ficam prontos apenas por importar um JSON.

### 6. Saber o que um teste comprova

Os dez testes originais passavam apesar das lacunas do robô. Os testes da API simulavam a resposta do scraper; comprovavam o contrato HTTP, não a busca.

A cobertura ampliada inclui páginas negativas, seleção de filtro, primeiro registro, detalhes, paginação, captura, timeout de fila e limpeza. Mesmo assim, testes locais não substituem a homologação do portal real.

## O que foi tecnicamente mais difícil de aplicar

Pela análise do código, a parte mais complexa é **sincronizar a navegação e validar que cada dado pertence à página e à pessoa corretas**. Ela combina esperas, múltiplas telas, identidade, seletores e tratamento de bloqueios. A API HTTP é relativamente pequena; a confiabilidade da coleta é onde se concentram as incertezas.

O obstáculo externo observado foi o WAF. Detectá-lo e responder com erro foi possível; comprovar os seletores reais não foi. Não houve quebra nem solução automática de CAPTCHA.

Uma forma honesta de explicar na apresentação: “A maior complexidade técnica está no fluxo entre pesquisa, panorama e benefícios. A revisão identificou transições faltantes e falsos positivos no parser. Implementei testes locais dessas etapas; a validação no portal público permanece limitada pela verificação humana.” Use “implementei” apenas para trabalho que você tenha executado ou possa explicar com propriedade.

## Critérios para concluir a entrega

1. Conferir e ajustar seletores em uma sessão autorizada que consiga acessar o portal.
2. Executar os cenários oficiais e inspecionar a evidência de cada sucesso.
3. Demonstrar consultas paralelas bem-sucedidas e seu isolamento.
4. Importar o workflow, configurar OAuth e conferir arquivo e planilha.
5. Publicar e testar a API online se apresentar a Parte 2.
6. Preencher links reais na entrega e informar limitações remanescentes.
