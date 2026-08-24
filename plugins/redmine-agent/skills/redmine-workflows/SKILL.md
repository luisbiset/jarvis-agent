---
name: redmine-workflows
description: Consultar e gerenciar projetos, chamados, comentários, status, responsáveis e horas no Redmine da SESAB. Usar quando o usuário pedir para localizar, resumir, criar ou atualizar chamados do Redmine, acompanhar suas pendências, registrar trabalho ou preparar triagens e relatórios a partir dos tickets.
---

# Fluxos do Redmine SESAB

Aplicar `FLOW-002`: nenhuma leitura, análise, plano ou gate anterior autoriza implicitamente comentário, status, horas ou outra escrita no Redmine. A mutação exige pedido e confirmação próprios.

Usar as ferramentas do servidor `redmine` para acessar dados reais. Não substituir a integração por pesquisa web quando o pedido envolver chamados privados.

## Conectar com segurança

- Usar somente `https://redmine.saude.ba.gov.br/`, salvo alteração explícita do proprietário.
- Exigir `REDMINE_API_KEY` no ambiente do processo. Nunca pedir que a chave seja colada na conversa, nunca exibi-la e nunca gravá-la no plugin.
- Se a autenticação falhar, informar apenas o código HTTP e orientar a conferir se a API REST está habilitada e se a chave está disponível localmente.
- Não desabilitar validação TLS e não contornar VPN, proxy ou política de rede.

## Consultar

1. Quando o usuário disser "meus chamados", obter primeiro o usuário atual e filtrar `assigned_to_id` como `me`.
2. Listar resultados de forma concisa: ID, assunto, projeto, status, prioridade, responsável e última atualização.
3. Buscar o chamado individual antes de responder perguntas sobre descrição, histórico, campos personalizados ou próxima ação.
4. Consultar metadados e membros do projeto antes de sugerir IDs de status, tracker, prioridade, atividade ou responsável.
5. Paginar quando houver mais resultados; não afirmar que uma lista está completa se a API indicar itens restantes.

## Alterar

Tratar `create_issue`, `add_issue_note`, `update_issue` e `log_time` como escrita em produção.

1. Obter o estado atual do chamado e os metadados necessários.
2. Preparar um resumo do efeito, incluindo chamado, campos, texto e horas que serão enviados.
3. Pedir confirmação explícita imediatamente antes de chamar a ferramenta de escrita, mesmo que a intenção anterior pareça clara.
4. Após a confirmação, executar uma única vez. Não repetir automaticamente uma escrita cujo resultado seja incerto por timeout.
5. Consultar novamente o chamado quando for importante comprovar o estado final.
6. Relatar exatamente o que mudou e apresentar o ID/link do chamado.

Nunca expor ferramenta de exclusão. Não encerrar chamado, trocar responsável, alterar prioridade, editar estimativa ou lançar horas sem mostrar o valor proposto na confirmação.

## Criar chamados

- Confirmar projeto, tracker, assunto e descrição.
- Resolver IDs a partir dos metadados em vez de adivinhá-los.
- Manter descrições factuais e rastreáveis. Distinguir comportamento observado, esperado, evidência e critérios de aceite.
- Não incluir credenciais, dados de pacientes, dumps ou informação pessoal desnecessária.

## Registrar horas

- Confirmar chamado ou projeto, data, quantidade de horas, atividade e comentário.
- Nunca registrar horas em nome de outro usuário.
- Não arredondar nem alterar a quantidade informada sem avisar.

## Resumir e triar

- Separar fatos existentes no Redmine de inferências do agente.
- Ao priorizar, declarar os critérios usados; não modificar prioridade ou status durante uma análise.
- Não reproduzir dados pessoais desnecessários. Resumir o histórico preservando decisões, bloqueios e próximas ações.
- Fornecer links no formato `https://redmine.saude.ba.gov.br/issues/<id>`.

## Limites

- Respeitar as permissões retornadas pelo Redmine; um erro 403 não autoriza tentativa com outra identidade.
- Não usar impersonação de usuário.
- Não anexar arquivos nesta versão do agente.
- Não executar alterações em lote. Preparar uma lista e solicitar autorização específica antes de cada conjunto claramente delimitado.
