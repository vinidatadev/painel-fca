# Documentação do Fluxo FCA (Ficha de Correção de Ação)

---

## Visão Geral

O fluxo gerencia o ciclo de vida de um FCA (Ficha de Correção de Ação), desde o registro pelo solicitante até a conclusão/devolutiva ao setor que abriu o chamado.

O processo envolve:
- Triagem automática por empresa e setor causador
- Notificação por e-mail ao responsável pelo tratamento
- Resposta via formulário vinculado ao card
- Devolutiva automática ao solicitante
- Possibilidade de redirecionamento para outro setor (caso FCA aberto incorretamente)

---

## Empresas

| Sigla | Nome Completo |
|-------|---------------|
| ACI - Matriz | Aço Cearense Industrial - Matriz |
| ACI - Filial | Aço Cearense Industrial - Filial |
| SINOBRAS | SINOBRAS |
| ACC | Aço Cearense Comercial |

---

## Setores por Empresa

| Setor | ACI Matriz | ACI Filial | SINOBRAS | ACC |
|-------|:----------:|:----------:|:--------:|:---:|
| ACL | ✅ | ✅ | ✅ | ❌ |
| PCP | ✅ | ✅ | ✅ | ❌ |
| Qualidade | ✅ | ✅ | ✅ | ❌ |
| MEP | ✅ | ✅ | ✅ | ❌ |
| Expedição | ✅ | ✅ | ✅ | ❌ |
| Produção | ✅ | ✅ | ✅ | ❌ |
| Comercial | ❌ | ❌ | ❌ | ✅ |
| Customer Service | ❌ | ❌ | ❌ | ✅ |

> Produção existe apenas como área causadora. Não abre FCA, portanto não possui fase de retorno.
> Customer Service administra o sistema e também pode abrir FCA, por isso possui fase de retorno.

---

## Estrutura de Fases

### Fase de Entrada
| Fase | Descrição |
|------|-----------|
| `0. Recebimento do Card` | Todo card novo entra aqui antes da triagem automática |

### Fases de Tratamento

#### ACI - Matriz
| Fase | Setor |
|------|-------|
| `1. ACL Matriz` | ACL |
| `3. PCP Matriz` | PCP |
| `4. Qualidade Matriz` | Qualidade |
| `5. MEP Matriz` | MEP |
| `6. Expedição Matriz` | Expedição |
| `8. Produção Matriz` | Produção |

#### ACI - Filial
| Fase | Setor |
|------|-------|
| `1. ACL Filial` | ACL |
| `3. PCP Filial` | PCP |
| `4. Qualidade Filial` | Qualidade |
| `5. MEP Filial` | MEP |
| `6. Expedição Filial` | Expedição |
| `8. Produção Filial` | Produção |

#### SINOBRAS
| Fase | Setor |
|------|-------|
| `1. ACL Sinobras` | ACL |
| `3. PCP Sinobras` | PCP |
| `4. Qualidade Sinobras` | Qualidade |
| `5. MEP Sinobras` | MEP |
| `6. Expedição Sinobras` | Expedição |
| `8. Produção Sinobras` | Produção |

#### ACC (exclusivos)
| Fase | Setor |
|------|-------|
| `2. Comercial` | Comercial |
| `7. Customer Service` | Customer Service |

Total: 20 fases de tratamento

### Fases de Retorno (devolutiva ao solicitante)

| Fase | Setor Solicitante |
|------|-------------------|
| `Retorno 1. ACL` | ACL |
| `Retorno 4. Qualidade` | Qualidade |
| `Retorno 5. MEP` | MEP |
| `Retorno 6. Expedição` | Expedição |
| `Retorno 7. Customer Service` | Customer Service |

> Produção não possui fase de retorno pois não atua como solicitante.
> Comercial não possui fase de retorno pelos mesmos motivos.

### Fases Auxiliares
| Fase | Função |
|------|--------|
| `Encaminha para outra área` | Passagem para redirecionamento quando FCA foi aberto para o setor errado |
| `Concluído` | Fase de passagem antes do roteamento para o retorno ao solicitante |

---

## Formulário de Abertura do FCA

Preenchido pelo solicitante na criação do card. Todos os campos são obrigatórios.

| Campo | Tipo | Opções |
|-------|------|--------|
| Causa do FCA | Lista | Carro com problema mecânico / Excesso de PBT / Formatação da carga (Erro roteirização/material frágil) / Material indisponível / Material obstruído / Material oxidado / Pedido fora do padrão (Emissão errada) / Peso fardo 1 tonelada / Divergência de peso como problema e repesar |
| Setor Solicitante | Lista | ACL / Customer Service / MEP / Qualidade / Expedição |
| Empresa do Solicitante | Lista | ACI - Matriz / ACI - Filial / ACC / SINOBRAS |
| Área Causadora | Lista | ACL / Comercial / MEP / PCP / Qualidade / Expedição / Produção |
| Empresa do Causador | Lista | ACI - Matriz / ACI - Filial / ACC / SINOBRAS |
| Ação | Lista | Ajustar a carga / Analisar e atuar junto com comercial / Atuar junto com comercial / Avaliar o material, se retira ou não de DT / Bloquear os fardos (Avaliar) / Confere o estoque e a programação do item junto com PCP / Sinalizar o time comercial / Desobstruir material / Corrigir peso como solução |
| UF | Lista | AC / AL / AM / AP / BA / CE / DF / GO / MA / MG / MT / PA / PB / PE / PI / PR / RJ / RN / RR / SC / SE / SP / TO / MS |
| Número da Remessa | Número | — |
| Detalhe / Observação | Texto livre | — |
| Nome | Texto livre | — |
| Matrícula | Número | — |
| Turno | Lista | A / B / C / D |
| Anexo / Evidência | Arquivo | — |

---

## Fluxo Detalhado

### Etapa 1 — Criação do Card

1. O solicitante preenche o formulário de abertura com todos os dados do FCA.
2. O card é criado e entra automaticamente na fase `0. Recebimento do Card`.

---

### Etapa 2 — Triagem Automática

Disparada ao entrar em `0. Recebimento do Card`.

Lógica: lê **Área Causadora** + **Empresa do Causador** e move para a fase correspondente.

Tabela de mapeamento completa:

| Área Causadora | Empresa do Causador | Fase de Destino |
|----------------|---------------------|-----------------|
| ACL | ACI - Matriz | `1. ACL Matriz` |
| ACL | ACI - Filial | `1. ACL Filial` |
| ACL | SINOBRAS | `1. ACL Sinobras` |
| Comercial | ACC | `2. Comercial` |
| PCP | ACI - Matriz | `3. PCP Matriz` |
| PCP | ACI - Filial | `3. PCP Filial` |
| PCP | SINOBRAS | `3. PCP Sinobras` |
| Qualidade | ACI - Matriz | `4. Qualidade Matriz` |
| Qualidade | ACI - Filial | `4. Qualidade Filial` |
| Qualidade | SINOBRAS | `4. Qualidade Sinobras` |
| MEP | ACI - Matriz | `5. MEP Matriz` |
| MEP | ACI - Filial | `5. MEP Filial` |
| MEP | SINOBRAS | `5. MEP Sinobras` |
| Expedição | ACI - Matriz | `6. Expedição Matriz` |
| Expedição | ACI - Filial | `6. Expedição Filial` |
| Expedição | SINOBRAS | `6. Expedição Sinobras` |
| Customer Service | ACC | `7. Customer Service` |
| Produção | ACI - Matriz | `8. Produção Matriz` |
| Produção | ACI - Filial | `8. Produção Filial` |
| Produção | SINOBRAS | `8. Produção Sinobras` |

---

### Etapa 3 — Notificação ao Responsável (E-mail de Abertura)

Disparado ao entrar na fase de tratamento correspondente.

Observação: para fases ACL, o campo UF é incluído no assunto do e-mail para facilitar a identificação de responsabilidade por estado.

Modelo do e-mail:

```
Assunto: Novo FCA Registrado - [Área Causadora] - [UF]   (UF somente para fases ACL)

Prezados,

Informamos que foi registrado um novo FCA. Seguem os detalhes:

CodFCA: [codigo_do_card]
________________________________________
Causa do FCA:         [causa_do_fca]
Setor Responsável:    [setor_solicitante]
Área Causadora:       [area_causadora]
Ação:                 [acao]
UF:                   [uf]
Empresa:              [empresa_do_causador]
Número da Remessa:    [numero_remessa]
Detalhe / Observação: [detalhe_observacao]

[acao]

GT: [gt] / DT: [dt]   (quando aplicável)
________________________________________

Para acessar o registro completo, clique no link abaixo:
👉 Visualizar e Tratar FCA

Atenciosamente,
Customer Service
```

---

### Etapa 4 — Tratamento pelo Responsável (Formulário de Resposta)

O responsável clica no link do e-mail e acessa o formulário de resposta vinculado ao card.

O formulário exibe primeiro um preview somente leitura com os dados da solicitação:

```
Causa do FCA:         [causa_do_fca]
Setor Responsável:    [setor_solicitante]
Área Causadora:       [area_causadora]
Ação:                 [acao]
UF:                   [uf]
Empresa:              [empresa_do_causador]
Número da Remessa:    [numero_remessa]
Detalhe:              [detalhe_observacao]
GT: [gt] / DT: [dt]
```

Em seguida os campos de resposta:

| Campo | Tipo | Obrigatório |
|-------|------|-------------|
| Problema Solucionado? | Seleção única: Sim / Não | Sim |
| Detalhe / Devolutiva da Tratativa | Texto livre | Sim |
| Encaminha para outra área? (FCA aberto incorreto) | Seleção única: Sim / Não | Sim |

Se "Encaminha para outra área?" = Sim, dois campos adicionais aparecem:

| Campo | Tipo | Opções |
|-------|------|--------|
| Área para encaminhamento | Lista | ACL / Comercial / MEP / PCP / Qualidade / Expedição / Produção / Customer Service |
| Empresa do setor para encaminhamento | Lista | ACI - Matriz / ACI - Filial / ACC / SINOBRAS |

---

### Etapa 5 — Roteamento pós-resposta

#### Cenário A — Conclusão normal (Encaminha para outra área? = Não)

Independente de "Problema Solucionado?" ser Sim ou Não:

1. Card vai para a fase `Concluído` (fase de passagem, sem dados armazenados)
2. Automação lê o campo **Setor Solicitante** e move para a fase de retorno correspondente:

| Setor Solicitante | Fase de Retorno |
|-------------------|-----------------|
| ACL | `Retorno 1. ACL` |
| Qualidade | `Retorno 4. Qualidade` |
| MEP | `Retorno 5. MEP` |
| Expedição | `Retorno 6. Expedição` |
| Customer Service | `Retorno 7. Customer Service` |

3. Ao entrar na fase de retorno, automação dispara o e-mail de devolutiva direcionado à **Empresa do Solicitante**.

#### Cenário B — Redirecionamento (Encaminha para outra área? = Sim)

1. Card vai para a fase `Encaminha para outra área` (fase de passagem)
2. Automação lê **Área para encaminhamento** + **Empresa do setor para encaminhamento**
3. Move o card para a fase de tratamento correspondente (mesma lógica da Etapa 2)
4. O novo responsável recebe o e-mail de abertura e trata o FCA normalmente (Etapas 3 a 5)

> Um FCA pode ser redirecionado mais de uma vez, repetindo o ciclo a cada redirecionamento.

---

### Etapa 6 — E-mail de Devolutiva (Retorno ao Solicitante)

Disparado ao entrar na fase de retorno correspondente ao setor solicitante.

Modelo do e-mail:

```
Assunto: FCA Respondido - [Área Causadora] - [CodFCA]

Prezados,

Informamos que foi respondido/solucionado o FCA registrado para a área: [setor_solicitante]

Seguem os detalhes:

Problema Solucionado?              [sim_ou_nao]
Detalhe / Devolutiva da Tratativa: [devolutiva]

Dados de Registro:
CodFCA: [codigo_do_card]
________________________________________
Causa do FCA:         [causa_do_fca]
Setor Responsável:    [setor_solicitante]
Área Causadora:       [area_causadora]
Ação:                 [acao]
UF:                   [uf]
Empresa:              [empresa_do_solicitante]
Número da Remessa:    [numero_remessa]
Detalhe / Observação: [detalhe_observacao]
DT: [dt]  /  GT: [gt]
________________________________________

Atenciosamente,
Customer Service
```

---

## Resumo do Fluxo (visão macro)

```
[Abertura do FCA pelo solicitante]
            |
            v
  [0. Recebimento do Card]
            |
            | automação: Área Causadora + Empresa do Causador
            v
  [Fase de Tratamento correspondente]
            |
            | dispara e-mail ao responsável
            |
            | responsável acessa link e preenche formulário de resposta
            v
     Encaminha para outra área?
            |
           Não                          Sim
            |                            |
            v                            v
       [Concluído]            [Encaminha para outra área]
       (passagem)                      (passagem)
            |                            |
            | automação:                 | automação: nova área + empresa
            | Setor Solicitante          v
            v                  [Nova fase de tratamento]
  [Fase de Retorno]                      |
            |                            | (repete o ciclo)
            | dispara e-mail             v
            | de devolutiva            ...
            v
     [FCA encerrado]
```

---

## Regras de Negócio

- Todo card passa obrigatoriamente por `0. Recebimento do Card` antes de ser roteado.
- A triagem automática usa sempre **Área Causadora + Empresa do Causador**.
- A devolutiva é direcionada sempre com base em **Setor Solicitante + Empresa do Solicitante**.
- ACC só possui os setores Comercial e Customer Service — combinações inválidas (ex: ACL + ACC) não devem ser permitidas no formulário.
- Produção é exclusivamente área causadora — nunca abre FCA e não possui fase de retorno.
- Produção existe nas empresas ACI Matriz, ACI Filial e SINOBRAS apenas.
- Comercial existe exclusivamente na ACC — não possui fase de retorno.
- Customer Service existe exclusivamente na ACC, administra o sistema e pode abrir FCA, portanto possui fase de retorno.
- O campo UF aparece no assunto do e-mail apenas para fases ACL.
- A fase `Concluído` é apenas de passagem — nenhum dado é armazenado nela.
- Um FCA pode ser redirecionado múltiplas vezes sem limite definido.
- Independente de "Problema Solucionado?" ser Sim ou Não, o fluxo segue para retorno — a diferença fica registrada no campo de resposta e no e-mail de devolutiva.
