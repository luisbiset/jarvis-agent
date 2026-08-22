---
name: sesab-orchestration
description: Orquestrar chamados do Redmine que gerem trabalho no SFA ou AGHUse e mudanças que envolvam integrações ou contratos compartilhados entre os sistemas. Usar também quando o usuário pedir explicitamente o orquestrador principal. Para consultas puras de Redmine ou tarefas isoladas em um sistema, preferir o workflow ou coordenador específico.
---

# Orquestração Redmine, SFA e AGHUse

## Orientação de uso

Quando o usuário pedir como usar, exemplos de prompts, onboarding, manutenção ou solução de problemas deste conjunto de agents, ler [references/guia-de-uso.md](references/guia-de-uso.md) e responder a partir dele. Não carregar o guia em tarefas comuns de implementação ou consulta.

## Classificar a tarefa

1. Identificar os repositórios e preservar seus estados do Git.
2. Se houver chamado, usar `redmine-workflows` para obter requisitos e manter o ID como rastreabilidade.
3. Classificar a tarefa como Redmine, SFA, AGHUse ou transversal.
4. Se estiver isolada, encaminhar ao workflow ou coordenador correspondente sem carregar os outros domínios.
5. Se for transversal, manter neste orquestrador a decisão do contrato e delegar a implementação.

## Roteamento

| Domínio | Coordenador/workflow | Especialistas ou finalidade |
|---|---|---|
| Redmine | `redmine-workflows` | Requisitos, pendências, comentários, status e horas |
| SFA | `sfa-development` | `sfa_frontend`, `sfa_backend`, `sfa_database`, `sfa_tests` |
| AGHUse | `aghuse-development` | `aghuse_frontend`, `aghuse_backend`, `aghuse_database`, `aghuse_tests` |
| Qualidade final | este orquestrador | `sesab_reviewer`, depois `qa_homologacao` quando houver fluxo executável |

Usar somente os especialistas necessários. Paralelizar exploração, revisão e testes independentes. Em implementação, atribuir arquivos sem sobreposição e sequenciar mudanças quando compartilharem contrato.

Antes de declarar uma implementação pronta para homologação, acionar `sesab_reviewer` em modo somente leitura. Corrigir achados bloqueantes e repetir a revisão quando o diff mudar materialmente. Acionar `qa_homologacao` quando existir ambiente local ou de homologação no escopo; ele deve produzir roteiro e evidências sem usar produção nem dados reais.

## Integrar o Redmine

- Ao receber um ID de chamado, consultar assunto, descrição, projeto, status, prioridade, responsável, campos relevantes e comentários recentes.
- Consultar relações e anexos somente quando necessários para esclarecer o requisito.
- Separar requisitos confirmados, hipóteses e lacunas. Não transformar comentário ambíguo em regra de negócio sem evidência.
- Não criar ou alterar chamado, comentário, status, responsável, prioridade ou horas sem pedido explícito.
- Nunca inferir horas trabalhadas. Registrar somente data, duração, atividade e comentário confirmados pelo usuário.
- Após a validação técnica, preparar um resumo com escopo, mudanças, testes e limitações. Publicar no Redmine somente quando solicitado.
- Não publicar credenciais, URLs privadas, dados clínicos, identificadores pessoais, dumps, payloads integrais ou detalhes internos desnecessários.

## Definir contrato transversal

Antes de editar, registrar:

- produtor, consumidor e responsabilidade de cada sistema;
- endpoint, evento ou arquivo, método e autenticação;
- request/response, tipos, nulabilidade, encoding, datas, timezone e competência;
- erros, status, timeout, retry, idempotência e observabilidade;
- compatibilidade retroativa, rollout, rollback e ordem de implantação;
- dados sensíveis e estratégia de anonimização nos testes.

Não presumir atomicidade entre os bancos ou runtimes. Quando houver escrita nos dois sistemas, explicitar consistência, compensação e comportamento de falha parcial.

## Integrar com segurança

- Não aplicar padrões Angular/Spring do SFA ao JSF/Java EE do AGHUse, nem o inverso.
- Preservar contratos existentes até que produtor e consumidor possam migrar com segurança.
- Não conectar a infraestrutura real, executar deploy ou alterar banco compartilhado sem autorização explícita.
- Nunca expor credenciais, URLs privadas, dados clínicos, pacientes, profissionais ou faturamento.

## Validar e concluir

Validar cada repositório com seu fluxo próprio. Depois validar o contrato entre os sistemas usando mocks, fixtures e dados fictícios. Consolidar: resultado, evidências, chamado relacionado, decisões, especialistas, arquivos por repositório, contrato, comandos, ordem de implantação, riscos, limitações e handoffs. Diferenciar claramente “implementado”, “revisado” e “homologado”.
