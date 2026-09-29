# Checklist de entrega

Estado em 29/09/2026: entrega parcial, ainda sem homologacao completa do portal headless e do bonus Google.

## Evidencias existentes

- Codigo versionado em https://github.com/fernandosantosb30/desafio-transparencia-bot (privado).
- Testes locais de unidade, API e Chromium em portal sintetico.
- CI aprovado: https://github.com/fernandosantosb30/desafio-transparencia-bot/actions/runs/36643354292.
- CI inclui build Docker, testes dentro do container e health/OpenAPI por HTTP.
- Inspecao interativa da busca, panorama e detalhes de dois programas no portal real.
- Documentacao de escolhas tecnicas, dificuldades, configuracao e limitacoes.

## Obrigatorio antes de afirmar funcionamento completo

1. Executar o scraper headless em acesso legitimo ao portal. O ultimo teste foi bloqueado por verificacao humana; aumentar o timeout nao resolve esse bloqueio por si so.
2. Conferir nome, CPF/NIS, primeiro resultado equivalente, filtro social, panorama, PNG Base64 e todas as paginas dos beneficios. Cobrir os tres programas e entradas sem resultado.
3. Demonstrar duas consultas simultaneas sem mistura de dados e com fechamento dos navegadores.

## Bonus

1. Concluir o primeiro deploy Railway do repositorio confirmado. Projeto e servico api existem, com Dockerfile, healthcheck e API_KEY configurados; ainda nao ha deployment ativo nem URL publica validada.
2. Confirmar /health e /docs por HTTPS, 401 em /consulta sem chave e uma chamada autenticada. Health 200 nao significa coleta real funcionando.
3. Preparar instancia n8n com armazenamento persistente, usuario proprietario e acesso restrito. Nao publicar uma instancia sem configuracao inicial.
4. Importar workflows/n8n_workflow.json, configurar URL da API e credencial X-API-Key.
5. Autorizar Google no proprio n8n, configurar pasta Drive e planilha com aba Consultas. A conexao Google do chat nao transfere credenciais ao n8n.
6. Executar uma consulta real e conferir arquivo [UUID]_[datetime].json, conteudo e linha com o mesmo UUID, data e link. Um arquivo com status erro testa o transporte, mas nao comprova coleta bem-sucedida.

## Pacote ao recrutador

- Conceder acesso ao repositorio privado ao destinatario correto, ou anexar arquivo do codigo sem .env, tokens, dados pessoais, .venv ou artefatos de consultas.
- Incluir README, RELATORIO, workflow exportado sem credenciais, link CI e URL da API somente depois de validada.
- Preparar demonstracao curta e exemplos anonimizados, separando testes sinteticos de resultados reais.
- Revisar docs/email_entrega.md, informar o que permanece pendente e nao apresentar o bonus como concluido sem evidencia ponta a ponta.
- Nao enviar chave no repositorio. Compartilha-la por canal privado apenas com o avaliador autorizado e revoga-la depois da avaliacao.
