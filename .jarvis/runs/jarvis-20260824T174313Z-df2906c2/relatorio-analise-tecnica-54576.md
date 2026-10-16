# Relatório de Análise Técnica de Viabilidade

## Tarefa 54576 — Pendências de Autorização

- **Sistema:** AGHUse
- **Área:** Faturamento hospitalar
- **Tipo:** Análise técnica de viabilidade
- **Data da análise:** 24/08/2026
- **Modalidade:** Somente leitura — sem implementação ou alteração de dados

## 1. Objetivo

Avaliar a viabilidade de permitir que uma instituição utilize o fluxo de
Pendências de Autorização de forma manual, sem integração efetiva com a SMS,
preservando:

- o registro das justificativas;
- a identificação do profissional responsável pela autorização;
- o funcionamento das listas de pendências;
- a geração do arquivo do Encerramento de Competência;
- o comportamento atual das instituições que utilizam autorização automática;
- o comportamento atual das instituições que possuem integração real com a SMS.

## 2. Fontes consultadas

- Requisitos e histórico da tarefa 54576 no Redmine.
- Histórico relacionado da tarefa 51557.
- Anexo “Pendência de Autorização”.
- Anexo “Encerramento de contas hospitalares”.
- Código-fonte do módulo `aghu-faturamento`.
- Código da branch atual e comparação somente leitura com a referência local
  `SESAB/master`.

Não foram utilizados dados reais de pacientes, credenciais, conexões com banco
ou acesso a ambientes compartilhados.

## 3. Resultado executivo

A demanda é **tecnicamente viável**.

A abordagem recomendada é criar um modo parametrizado de **autorização manual
local**, habilitado explicitamente por instituição, no qual a autorização feita
na tela conclua localmente o processo da conta.

Essa conclusão deve ocorrer sem simular o envio ou o retorno de um arquivo da
SMS e sem flexibilizar os critérios do Encerramento de Competência.

### Classificação

| Aspecto | Avaliação |
|---|---|
| Viabilidade | Viável |
| Complexidade técnica | Média |
| Risco operacional | Alto |
| Alteração estrutural de banco | Não necessária |
| Alteração do arquivo da competência | Não recomendada |
| Compatibilidade comunitária | Preservável por parâmetro opt-in |

O risco operacional é considerado alto porque `IND_AUTORIZADO_SMS` funciona
como um gate para a seleção de contas no faturamento da competência.

## 4. Fluxo atual identificado

### 4.1 Alta hospitalar

Quando uma conta é criada ou passa para a situação de alta:

- com a integração configurada como `N`, o sistema preenche automaticamente
  `IND_ENVIADO_SMS=S` e `IND_AUTORIZADO_SMS=S`;
- com a integração configurada como `S`, a conta permanece aguardando o fluxo
  de autorização.

O processo de alta não preenche `DT_ENVIO_SMS`, `IND_AUDITORIA` nem o auditor
responsável.

**Evidência principal:**
`aghu/aghu-faturamento/src/main/java/br/gov/mec/aghu/faturamento/business/ContaHospitalarRN.java`.

### 4.2 Ação “Enviar” no Encerramento/Prévia

A ação executada na tela é uma operação local. Ela:

- define `IND_ENVIADO_SMS=S`;
- registra um extrato com situação `E` e descrição de envio;
- preserva a justificativa informada;
- não realiza, nesse momento, uma chamada externa para a SMS.

O arquivo de integração e o processamento do retorno pertencem a etapas
separadas.

**Evidências principais:**

- `aghu/aghu-faturamento/src/main/java/br/gov/mec/aghu/faturamento/business/ContaHospitalarON.java`;
- `aghu/aghu-faturamento/src/main/java/br/gov/mec/aghu/faturamento/business/ExtratoContasON.java`;
- `aghu/aghu-faturamento/src/main/java/br/gov/mec/aghu/faturamento/action/EncerramentoPreviaContaController.java`.

### 4.3 Critérios da lista de pendências

A consulta principal seleciona contas que atendem, entre outros, aos seguintes
critérios:

- situação da conta igual a `E`;
- `IND_ENVIADO_SMS=S`;
- `DT_ENVIO_SMS IS NULL`;
- `IND_AUTORIZADO_SMS IS NULL`;
- empresa correspondente ao contexto selecionado.

Também são considerados filtros pessoais/configuráveis, como especialidade ou
clínica, paciente, dia e turno.

Existe uma consulta complementar que não repete explicitamente o critério de
`IND_AUTORIZADO_SMS IS NULL`, mas exige `DT_ENVIO_SMS IS NULL`. Por isso, o
preenchimento da data deve ser mantido no fluxo local para impedir o
reaparecimento da conta.

**Evidência principal:**
`aghu/aghu-faturamento/src/main/java/br/gov/mec/aghu/faturamento/dao/FatContasHospitalaresDAO.java`.

### 4.4 Seleção da conta pelo auditor

Ao selecionar uma conta, o sistema utiliza `IND_AUDITORIA` e o servidor de
auditoria para controle de posse/bloqueio do trabalho.

Esses campos não substituem o extrato como trilha permanente da autorização.
O autor da operação, a data e a justificativa ficam registrados principalmente
em `FAT_EXTRATO_CONTAS`.

**Evidência principal:**
`aghu/aghu-faturamento/src/main/java/br/gov/mec/aghu/faturamento/business/FatContasHospitalaresON.java`.

### 4.5 Autorização manual

O comportamento atual da autorização manual:

- grava um extrato com situação `A` e descrição “Autorizado”;
- registra data, servidor autenticado e justificativa, quando aplicável;
- preenche `DT_ENVIO_SMS` com a data atual e o horário configurado;
- não preenche `IND_AUTORIZADO_SMS`.

Consequentemente, a conta continua dependente do retorno da integração para
receber `IND_AUTORIZADO_SMS=S`.

**Evidência principal:**
`aghu/aghu-faturamento/src/main/java/br/gov/mec/aghu/faturamento/business/ExtratoContasON.java`.

### 4.6 Arquivo e retorno da SMS

O gerador do arquivo destinado à SMS seleciona contas com `DT_ENVIO_SMS`
preenchida e `IND_AUTORIZADO_SMS IS NULL`.

O processamento do retorno da SMS é responsável por preencher
`IND_AUTORIZADO_SMS=S`, além dos demais dados retornados pela integração.

**Evidências principais:**

- `aghu/aghu-faturamento/src/main/java/br/gov/mec/aghu/faturamento/dao/FatContasHospitalaresDAO.java`;
- `aghu/aghu-faturamento/src/main/java/br/gov/mec/aghu/faturamento/business/GerarArquivoSmsON.java`;
- `aghu/aghu-faturamento/src/main/java/br/gov/mec/aghu/faturamento/business/AtualizaAihRN.java`.

### 4.7 Encerramento de Competência

A geração do arquivo do Encerramento de Competência exige, entre outros
critérios:

- conta na situação `E`;
- AIH existente;
- `IND_AUTORIZADO_SMS=S`;
- competência, datas, empresa e entidade compatíveis com a geração.

A seleção não exige `IND_ENVIADO_SMS`, `DT_ENVIO_SMS` ou `IND_AUDITORIA`.

Portanto, não é necessário nem recomendável alterar o critério do arquivo da
competência. A solução local precisa concluir corretamente a autorização da
conta.

**Evidências principais:**

- `aghu/aghu-faturamento/src/main/java/br/gov/mec/aghu/faturamento/business/GeracaoArquivoFaturamentoCompetenciaInternacaoRN.java`;
- `aghu/aghu-faturamento/src/main/java/br/gov/mec/aghu/faturamento/dao/FatEspelhoAihDAO.java`.

## 5. Três soluções técnicas viáveis

Não existe alteração literalmente sem impacto, porque o indicador de autorização
participa diretamente do faturamento e da integração externa. As três soluções
abaixo foram desenhadas para manter o comportamento padrão, isolar a ativação e
evitar mudanças nas consultas financeiras consolidadas.

| Posição | Solução | Impacto técnico | Isolamento | Indicação |
|---|---|---|---|---|
| 1 | Chave adicional no fluxo existente | Baixo | Alto | Menor alteração e melhor relação entre segurança e esforço |
| 2 | Comando explícito de autorização local | Médio | Muito alto | Quando a distinção precisa aparecer no contrato e na tela |
| 3 | Origem persistida da autorização | Médio/alto | Alto | Quando a rastreabilidade inequívoca é requisito formal |

### 5.1 Solução 1 — Chave adicional no fluxo existente

Esta é a solução recomendada.

Criar um segundo parâmetro funcional, preferencialmente multiempresa, com
significado equivalente a:

> Concluir a autorização localmente, sem aguardar retorno da SMS.

O nome definitivo do parâmetro deve seguir a convenção vigente no módulo e ser
aprovado na etapa de implementação.

#### Matriz de comportamento

| Integração atual | Autorização local | Comportamento esperado |
|---|---|---|
| `N` | `N` | Autorização automática na alta, sem alteração |
| `S` | `N` | Integração real com a SMS, sem alteração |
| `S` | `S` | Novo fluxo de autorização manual local |

O novo parâmetro deve ter valor padrão `N`. Assim, a instalação ou atualização
do sistema não modifica silenciosamente o comportamento de nenhuma instituição.

#### Operação de autorização no modo local

Quando o modo local estiver ativo, a autorização deve ocorrer na mesma
transação e executar:

1. registrar o extrato da autorização, com usuário, data e justificativa;
2. manter o preenchimento atual de `DT_ENVIO_SMS`;
3. preencher `IND_AUTORIZADO_SMS=S`;
4. preservar `IND_ENVIADO_SMS=S`, definido na etapa anterior do fluxo.

Esse conjunto produz os efeitos necessários:

- retira a conta das consultas de pendências;
- impede que a conta seja selecionada para envio à SMS;
- permite a seleção da conta pelo Encerramento de Competência;
- preserva a trilha de auditoria do usuário e da justificativa.

Recomenda-se utilizar uma descrição de extrato distinta, como “Autorizado
localmente”, para que a origem da autorização não seja confundida com um retorno
efetivo da SMS.

#### Vantagens

- menor conjunto de arquivos e menor superfície de regressão;
- comportamento padrão desabilitado e ativação isolada por empresa;
- preservação das consultas da Pendência, SMS e Competência;
- baixa complexidade de implantação e rollback da configuração.

#### Desvantagens e riscos residuais

- o mesmo indicador passa a representar autorização externa ou local;
- a origem precisa ser distinguida pelo extrato;
- ativação indevida em instituição integrada impediria o envio das novas contas;
- a granularidade por empresa pode ser insuficiente se uma empresa possuir
  unidades integradas e não integradas simultaneamente.

#### Quando escolher

Quando a prioridade for atender ao requisito com a menor alteração possível,
sem mudar contratos Java, tabelas ou consultas de faturamento.

### 5.2 Solução 2 — Comando explícito de autorização local

Criar uma operação de negócio distinta, por exemplo
`autorizarContaLocalmente`, mantendo a operação atual reservada ao processo de
integração.

O backend deve decidir qual operação é permitida a partir do parâmetro atual e
da nova chave de modo local. A decisão não pode depender somente da visibilidade
do botão na interface.

A operação local deve executar atomicamente:

- validação do auditor e do estado da conta;
- extrato `A`, preferencialmente com descrição “Autorizado localmente”;
- servidor, data e justificativa;
- preenchimento de `DT_ENVIO_SMS`;
- preenchimento de `IND_AUTORIZADO_SMS=S`.

#### Alterações prováveis

- novo método na facade/interface cliente e respectiva implementação;
- nova operação na ON, reutilizando rotina interna comum;
- seleção da operação no controller;
- comando e mensagens condicionais no XHTML;
- novo parâmetro de ativação;
- testes da ON e dos contratos afetados.

#### Preservação dos fluxos existentes

- configuração atual `N`: continua usando a autorização automática na alta;
- integração `S` com modo local `N`: utiliza exclusivamente a operação atual e
  aguarda o retorno da SMS;
- integração `S` com modo local `S`: utiliza exclusivamente a nova operação e
  conclui a autorização localmente.

#### Vantagens

- distinção semântica clara entre integração e autorização local;
- menor chance de evolução futura de um fluxo afetar o outro;
- interface, contrato e extrato podem evidenciar a origem da operação;
- regras de permissão e testes ficam mais explícitos.

#### Desvantagens e riscos residuais

- alteração em mais camadas e possível mudança no contrato `*-client`;
- risco de divergência entre a decisão do controller e a validação do backend;
- risco de exibição simultânea dos dois comandos;
- continua utilizando `IND_AUTORIZADO_SMS` para origens distintas.

#### Quando escolher

Quando for importante que operadores, logs, tela e contratos distingam
explicitamente a autorização local do processo de SMS.

### 5.3 Solução 3 — Origem persistida da autorização

Adicionar um atributo próprio para registrar a origem da autorização, com
domínio controlado, por exemplo:

- automática sem integração;
- retorno da integração SMS;
- autorização manual local.

O indicador legado `IND_AUTORIZADO_SMS=S` continuaria sendo preenchido em todos
os casos concluídos para preservar o Encerramento de Competência. O novo atributo
serviria para auditoria e suporte, sem substituir inicialmente os filtros
financeiros existentes.

Os três pontos de conclusão registrariam a origem correspondente: alta
automática, retorno externo ou comando local.

#### Alterações prováveis

- nova coluna em `FAT_CONTAS_HOSPITALARES`, ou estrutura equivalente aprovada;
- mapeamento na entidade e no histórico/journal;
- enum ou domínio compartilhado;
- ajustes nos três pontos que concluem a autorização;
- scripts idempotentes para Oracle e PostgreSQL, com rollback;
- tratamento explícito dos registros legados com origem nula;
- testes de persistência, histórico e compatibilidade.

#### Preservação dos fluxos existentes

- configuração atual `N`: mantém os indicadores atuais e registra origem
  automática;
- integração `S`: mantém autorização nula durante o envio e registra origem
  externa somente no retorno;
- modo local: preenche data, autorização e origem local na mesma transação.

#### Vantagens

- rastreabilidade inequívoca, independente da configuração atual;
- melhor suporte a auditoria e diagnóstico;
- permite novos canais de autorização sem inferência pelo extrato;
- mantém os filtros financeiros atuais durante a primeira implantação.

#### Desvantagens e riscos residuais

- maior custo técnico e operacional;
- exige alteração de schema, entidade e histórico;
- registros legados não terão origem confiável sem uma migração aproximada;
- exige coordenação de implantação entre scripts e aplicação;
- pode haver inconsistência se origem e indicador não forem gravados de forma
  centralizada e atômica.

#### Quando escolher

Quando a origem da autorização for requisito regulatório, de auditoria ou de
suporte, ou quando houver previsão concreta de novos canais de autorização.

## 6. Alternativas descartadas

### 6.1 Alterar o parâmetro atual

**Não recomendado.** O valor `S` atualmente representa o fluxo que aguarda a
integração. Fazer toda autorização manual preencher diretamente
`IND_AUTORIZADO_SMS=S` interromperia o envio das contas de instituições que
possuem integração real.

### 6.2 Manter o parâmetro atual em `N`

**Não atende ao requisito.** Nesse modo a autorização ocorre automaticamente na
alta, sem passar pela análise manual e pela justificativa esperadas pela unidade.

### 6.3 Simular geração e retorno da SMS

**Não recomendado.** Essa alternativa cria registros artificiais de integração,
aumenta o acoplamento, prejudica a rastreabilidade e adiciona etapas sem benefício
funcional.

### 6.4 Flexibilizar o arquivo da competência

**Não recomendado.** Permitir contas com `IND_AUTORIZADO_SMS IS NULL` no arquivo
da competência removeria uma proteção funcional existente e poderia incluir
contas ainda não autorizadas.

## 7. Escopo provável da solução recomendada

### Produção

- catálogo de parâmetros do faturamento;
- `ExtratoContasON`, para decidir entre conclusão local e espera pelo retorno;
- eventualmente a interface, apenas se for aprovada a troca dos termos “Enviar”
  ou “SMS” no modo local.

### Sem alteração funcional esperada

- critérios da lista de pendências;
- geração do arquivo da SMS;
- processamento do retorno da SMS;
- seleção do arquivo do Encerramento de Competência.

Uma mudança nesses componentes somente deve ocorrer se testes demonstrarem que
o contrato identificado não é suficiente.

## 8. Persistência e implantação da solução recomendada

Não foi identificada necessidade de:

- nova coluna;
- nova tabela;
- alteração de entidade JPA;
- mudança nas consultas do Encerramento de Competência.

Será necessário cadastrar o novo parâmetro e seu valor padrão. Caso a entrega
exija scripts Oracle e PostgreSQL, eles devem ser preparados de forma idempotente,
com aplicação e rollback externos ao repositório AGHUse, conforme o processo de
entrega da equipe.

## 9. Riscos e controles

| Risco | Consequência | Controle recomendado |
|---|---|---|
| Ativação indevida em instituição integrada | Contas deixam de ser enviadas à SMS | Parâmetro opt-in, padrão `N`, permissão restrita e implantação assistida |
| Autorização e extrato em transações diferentes | Estado inconsistente ou perda de auditoria | Atualização atômica na mesma transação |
| Uso isolado de `IND_AUTORIZADO_SMS=S` como prova de integração | Confusão entre autorização local e retorno externo | Descrição distinta no extrato e documentação do parâmetro |
| Granularidade inadequada do parâmetro | Fluxos mistos dentro da mesma empresa | Confirmar se a configuração deve ser por empresa, unidade ou entidade |
| Conta reaparecer em consulta complementar | Retrabalho ou dupla análise | Manter o preenchimento de `DT_ENVIO_SMS` |
| Reversão posterior do parâmetro | Contas já autorizadas permanecem concluídas | Definir tratamento funcional para contas anteriores à desativação |

## 10. Cenários mínimos de validação

### Fluxo automático atual

1. Integração configurada como `N`.
2. Realizar alta de uma conta fictícia.
3. Confirmar `IND_ENVIADO_SMS=S` e `IND_AUTORIZADO_SMS=S`.
4. Confirmar que a conta não aparece na lista de pendências.

### Integração real atual

1. Integração `S` e modo local `N`.
2. Enviar a conta pelo fluxo de encerramento/prévia.
3. Autorizar e gerar o arquivo da SMS.
4. Processar um retorno fictício.
5. Confirmar que somente o retorno conclui `IND_AUTORIZADO_SMS=S`.

### Novo modo local

1. Integração `S` e modo local `S`.
2. Enviar uma conta com justificativa.
3. Confirmar sua exibição na lista de pendências.
4. Selecionar e autorizar a conta.
5. Confirmar extrato, ator, justificativa e data.
6. Confirmar `DT_ENVIO_SMS` preenchida e `IND_AUTORIZADO_SMS=S`.
7. Confirmar ausência da conta nas pendências e no arquivo da SMS.
8. Confirmar presença da conta no arquivo da competência quando os demais
   critérios forem atendidos.

### Regressões complementares

- isolamento entre empresas;
- contas com filtros de especialidade, dia e turno;
- concorrência entre auditores;
- estorno de alta;
- reinternação;
- desdobramento de contas;
- rollback quando o horário de autorização estiver ausente ou inválido;
- desativação do parâmetro após existirem contas autorizadas localmente.

## 11. Decisões funcionais pendentes

Antes da implementação, devem ser respondidas as seguintes questões:

1. A justificativa será obrigatória na ação de envio?
2. O modo local será configurado por empresa, unidade ou entidade de saúde?
3. Existem empresas que possuem unidades integradas e não integradas ao mesmo
   tempo?
4. A autorização local valerá para todas as contas ou apenas para contas com
   determinadas ocorrências ou justificativas?
5. O extrato deverá registrar explicitamente “Autorizado localmente”?
6. Quais usuários ou perfis poderão ativar o parâmetro?
7. A interface deverá substituir as referências a “Enviar” e “SMS” quando o
   modo local estiver ativo?
8. Qual branch oficial será utilizada na implementação da tarefa 54576?

## 12. Condições para aprovação da solução

A solução poderá ser considerada aceita quando:

- os três modos da matriz funcionarem sem interferência entre si;
- a autorização local preservar usuário, data e justificativa;
- contas autorizadas localmente não forem enviadas à SMS;
- contas autorizadas localmente forem elegíveis para o arquivo da competência;
- o comportamento padrão após a atualização permanecer inalterado;
- os cenários de estorno, reinternação, desdobramento e multiempresa forem
  homologados;
- houver decisão documentada para todas as pendências funcionais relevantes.

## 13. Limitações da análise

- Não foram executados builds ou testes, pois não houve alteração de código.
- Não foi realizada conexão com banco, SMS, WildFly ou ambiente compartilhado.
- A branch ativa durante a inspeção era `feature/51087-01`, não relacionada à
  tarefa 54576. Os pontos críticos também foram comparados, sem troca de branch,
  com a referência local `SESAB/master`.
- A análise estabelece a viabilidade e a abordagem recomendada, mas não substitui
  a decisão funcional sobre a granularidade e a governança do novo parâmetro.

## 14. Parecer final

O fluxo manual sem integração real com a SMS pode ser implementado com impacto
localizado e sem mudança estrutural no banco.

O desenho mais seguro é preservar os comportamentos existentes e acrescentar um
modo local explicitamente habilitado. Nesse modo, a autorização manual deve
registrar a auditoria existente, manter `DT_ENVIO_SMS` e concluir
`IND_AUTORIZADO_SMS=S` na mesma transação.

A implementação deve permanecer bloqueada até a definição da granularidade do
parâmetro, da obrigatoriedade da justificativa, da identificação da origem no
extrato e da branch oficial de desenvolvimento.
