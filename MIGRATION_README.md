# Migração do Sistema de Folha de Pagamento

## Resumo das Alterações

O sistema de folha de pagamento foi reestruturado para permitir um melhor controle financeiro mensal. As principais mudanças são:

### 1. Estrutura do Banco de Dados

**Tabela `folha`:**
- Adicionado campo `mes_ano` (VARCHAR(7)) - formato YYYY-MM
- Adicionado campo `valor_total` (FLOAT) - soma de todos os pagamentos
- Adicionado campo `status` (VARCHAR(20)) - aberta, fechada, cancelada
- Adicionado campo `observacao` (TEXT)
- Adicionado índice na coluna `mes_ano`

**Tabela `pessoa_folha`:**
- Mantida a estrutura existente
- Relacionamento com `folha` através de `folha_id`

### 2. Fluxo de Trabalho

**Antes:**
1. Criar folha e associar pessoas simultaneamente
2. Dificuldade para controlar gastos mensais

**Depois:**
1. Criar folha (mês/ano específico)
2. Adicionar pessoas à folha individualmente
3. Controle automático do valor total
4. Status da folha (aberta/fechada/cancelada)

### 3. Funcionalidades Adicionadas

- **Criação de Folha:** Formulário dedicado para criar folhas por mês/ano
- **Gestão de Pessoas:** Adicionar/remover pessoas de uma folha específica
- **Controle Financeiro:** Valor total calculado automaticamente
- **Relatórios Melhorados:** Filtros por mês/ano e status
- **Exportação:** PDF e XLSX com informações consolidadas

## Instruções de Migração

### 1. Executar o Script de Migração

```bash
python migrate_folha.py
```

Este script irá:
- Adicionar as novas colunas à tabela `folha`
- Calcular valores totais para registros existentes
- Criar índices necessários
- Atualizar registros existentes com mês/ano

### 2. Verificar a Migração

Após executar o script, verifique se:

1. As colunas foram adicionadas corretamente:
```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'folha' 
ORDER BY column_name;
```

2. Os valores foram calculados:
```sql
SELECT mes_ano, valor_total, status 
FROM folha 
LIMIT 5;
```

### 3. Testar as Funcionalidades

1. **Criar uma nova folha:**
   - Acesse `/folhas`
   - Clique em "Nova Folha"
   - Preencha mês/ano e status

2. **Adicionar pessoas à folha:**
   - Na lista de folhas, clique no ícone "Adicionar Pessoa"
   - Selecione a pessoa e preencha os dados do pagamento

3. **Visualizar pessoas da folha:**
   - Clique no ícone "Ver Pessoas" para ver detalhes

4. **Gerar relatórios:**
   - Acesse o relatório de folhas
   - Use filtros por mês/ano
   - Exporte em PDF ou XLSX

## Estrutura de Arquivos Modificados

### Models
- `app/models.py` - Adicionados campos e métodos na classe `Folha`

### Forms
- `app/forms.py` - Novos formulários `PessoaFolhaForm` e `EditarPessoaFolhaForm`

### Templates
- `app/templates/folha/folha_form.html` - Formulário de criação/edição de folha
- `app/templates/folha/folha_list.html` - Lista de folhas com novos campos
- `app/templates/folha/folha_relatorio.html` - Relatório atualizado
- `app/templates/folha/pessoa_folha_form.html` - Formulário para adicionar pessoas
- `app/templates/folha/folha_pessoas.html` - Novo template para listar pessoas da folha

### Routes
- `app/routes.py` - Rotas atualizadas para o novo fluxo

### Scripts
- `migrate_folha.py` - Script de migração do banco de dados

## Benefícios da Nova Estrutura

1. **Controle Financeiro:** Valor total calculado automaticamente por mês
2. **Organização:** Folhas organizadas por mês/ano
3. **Flexibilidade:** Adicionar/remover pessoas independentemente
4. **Relatórios:** Melhor visualização dos gastos mensais
5. **Auditoria:** Histórico completo de alterações

## Rollback (se necessário)

Se precisar reverter as alterações:

1. Fazer backup dos dados
2. Executar comandos SQL para remover colunas:
```sql
ALTER TABLE folha DROP COLUMN IF EXISTS mes_ano;
ALTER TABLE folha DROP COLUMN IF EXISTS valor_total;
ALTER TABLE folha DROP COLUMN IF EXISTS status;
ALTER TABLE folha DROP COLUMN IF EXISTS observacao;
```

3. Restaurar versões anteriores dos arquivos

## Suporte

Em caso de problemas durante a migração, verifique:
- Logs do script de migração
- Permissões do banco de dados
- Backup dos dados antes da migração 