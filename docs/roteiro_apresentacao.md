# Roteiro de apresentação (slides)

1. Visão geral do problema e objetivos.
2. Arquitetura da solução: FastAPI + Playwright + módulos de parser e utilitários.
3. Fluxo de automação do robô e critérios de segurança.
4. API REST e contratos de resposta com OpenAPI.
5. Concorrência, erro e teste de robustez.
6. Parte 2: n8n, Google Drive e Google Sheets.
7. Resultados e limitações práticas do portal.
8. Próximos passos e melhorias futuras.

# Roteiro de demonstração prática

1. Subir a API localmente (`uvicorn app.main:app --host 0.0.0.0 --port 8000`).
2. Abrir `/docs` e mostrar a documentação Swagger.
3. Executar cinco consultas em paralelo com o CLI ou `curl` em lote.
4. Mostrar as respostas em JSON e evidências Base64.
5. Importar o workflow n8n e apontar para a API.
6. Executar a orquestração e mostrar a gravação do JSON no Drive.
7. Validar a linha adicionada na planilha do Google Sheets.

## Honestidade da demonstração

Os testes com Chromium usam um portal sintético. Demonstre-os como testes locais, sem apresentá-los como coleta real do governo. A revisão encontrou bloqueio Human Verification; a navegação no portal público e o bônus ainda exigem homologação.

Para falar de dificuldades, consulte `RELATORIO.md`: o problema central foi distinguir pesquisa, resultado, panorama e detalhes. Explique também por que os testes antigos passavam sem exercitar essas transições. Não afirme ter concluído OAuth, deploy ou superado CAPTCHA sem evidências.
