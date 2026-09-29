# n8n, Google Drive e Google Sheets

## Estado e fluxo

O arquivo `workflows/n8n_workflow.json` é um modelo corrigido, ainda não homologado em uma instância n8n com Google. Não contém credenciais nem IDs reais de pasta/planilha.

`Webhook -> HTTP Request -> Preparar JSON -> Google Drive -> Google Sheets`

O webhook responde ao recebimento; essa resposta não confirma que o Drive ou o Sheets terminaram. Confira a execução no n8n.

## Configuração

1. Importe o JSON. Mantenha o workflow inativo enquanto configura os serviços.
2. No HTTP Request, informe a URL da API. O padrão `host.docker.internal` atende a alguns ambientes Docker; em Linux pode exigir `extra_hosts: ["host.docker.internal:host-gateway"]` no serviço **n8n**. Entre serviços na mesma rede Compose, use o nome do serviço. Para o bônus online, use a URL HTTPS publicada.
3. Configure as credenciais OAuth2 dos nós Google pela interface do n8n e autorize a conta que tem acesso aos destinos. Configure a URI de redirecionamento indicada pela sua instância no cliente OAuth Google. Não exporte tokens para o Git.
4. No Drive, substitua `PASTA_GOOGLE_DRIVE_ID` no campo Parents. O nó usa a versão 1 com autenticação OAuth2 explícita e operação Upload. Caso o editor migre o nó, confira novamente seus parâmetros.
5. Crie uma planilha com aba `Consultas` e cabeçalhos: `identificador_unico`, `nome`, `cpf`, `data_hora`, `link_json`, `status`. Configure o ID da planilha no nó Sheets e recarregue o mapeamento das colunas.
6. Use a URL de teste que o nó Webhook mostra enquanto escuta uma execução. Depois da homologação, ative o workflow e use sua URL de produção. Restrinja o acesso ao webhook antes de publicá-lo.

Corpo de entrada:

```json
{"termo":"Maria da Silva","filtro_beneficiario_social":false}
```

O filtro é encaminhado ao robô. O nó Preparar JSON serializa a resposta inteira em UTF-8, cria um binário de MIME `application/json` e usa UUID mais data/hora da consulta no nome. Dois-pontos e pontos do timestamp são substituídos por hífens.

## Conferência da saída

- No Drive, confira extensão, conteúdo JSON, evidência e o UUID no nome do arquivo.
- No Sheets, o UUID, nome, CPF e timestamp vêm do nó HTTP Request. O ID retornado pelo Drive forma o link do arquivo.
- O modo RAW impede interpretar nomes como fórmulas e preserva strings. Append usa a operação de acréscimo de linhas da API.
- Respostas com `status: erro` também são arquivadas; a linha tem status de erro e nome/CPF vazios. Isso mantém rastreabilidade sem aparentar uma coleta válida.
- HTTP 422 ou falha HTTP interrompem o workflow antes do upload. Revise os dados de entrada e a conectividade.
- O link não torna o arquivo público. O acesso depende das permissões do Drive.

## Falhas e retomada

Não existe transação entre Drive e Sheets. Se o upload concluir e o Sheets falhar, pode existir um arquivo sem linha. Corrija a falha e retome o nó necessário; repetir o fluxo inteiro pode duplicar arquivos e consultas. Idempotência por `id_consulta` e reconciliação são melhorias futuras.

O histórico do n8n pode armazenar dados pessoais e a evidência. Configure acesso e retenção conforme o ambiente de uso. Não há comprovação de integração real nem publicação online nesta revisão.
