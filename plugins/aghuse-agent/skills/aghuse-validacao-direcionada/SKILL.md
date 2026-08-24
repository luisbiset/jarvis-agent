---
name: aghuse-validacao-direcionada
description: Selecionar e executar validações proporcionais aos arquivos alterados no AGHUse, mapeando módulos Maven, entidades, XHTML, mensagens e testes ON/RN. Usar para evitar builds e suítes amplas sem perder a cobertura direta da mudança.
---

# Validação direcionada do AGHUse

Use os subcomandos `modulos` e `validacao` de `scripts/aghuse_automacao.py` para obter sugestões iniciais. Confira os `pom.xml` antes de executar comandos gerados.

## Selecionar

- Entidades ou mapeamentos: instalar `aghu-entidades` antes dos consumidores.
- Java: compilar o menor módulo com `--projects` e `--also-make` quando adequado.
- XHTML: validar XML/Facelets e compilar o WAR correspondente.
- Mensagens: validar chaves usadas e duplicadas.
- ON/RN: localizar teste existente e executar apenas classes diretamente relacionadas.
- Alterações transversais: ampliar gradualmente somente após falha ou dependência demonstrada.

## Segurança

Não executar `.scripts-validate/dao-tests`, suíte completa, deploy ou integração externa automaticamente. Informar comandos executados, resultados, exclusões deliberadas e confiança residual.
