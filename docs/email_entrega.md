Assunto: Entrega do desafio de RPA e hiperautomação

Olá,

Segue a entrega do desafio técnico de automação web com Python e integração low-code.

Anexos / links:
- Código-fonte completo do robô + API FastAPI;
- README com instruções de instalação, execução e deploy;
- Dockerfile e docker-compose.yml;
- Workflow n8n exportado em `workflows/n8n_workflow.json`;
- Relatório técnico com decisões e limitações;
- Roteiro de apresentação e demonstração prática.

A solução inclui:
- automação do Portal da Transparência em headless;
- API REST com Swagger/OpenAPI;
- concorrência por semáforo;
- retorno padronizado de dados e evidência Base64;
- modelo de workflow para salvar JSON no Drive e registrar no Google Sheets.

Estado de validação: os testes locais incluem Chromium em um portal sintético. O GitHub Actions aprovou testes, build Docker, testes no container e verificação HTTP. A navegação interativa permitiu revisar parte dos seletores reais, mas o scraper headless ainda recebeu verificação humana. A integração Google e a publicação online ainda precisam de homologação; não estão sendo apresentadas como concluídas.

Código (privado; conceder acesso antes do envio): https://github.com/fernandosantosb30/desafio-transparencia-bot
Validação CI: https://github.com/fernandosantosb30/desafio-transparencia-bot/actions/runs/36643354292

Antes do envio, preencher: [LINK DO CÓDIGO], [URL DA API, SE PUBLICADA] e [EVIDÊNCIAS DOS TESTES REAIS]. Atualizar o estado acima somente depois da verificação correspondente.

Qualquer dúvida sobre a execução local ou a configuração do n8n, posso detalhar em um próximo passo.

Atenciosamente,
[Seu Nome]
