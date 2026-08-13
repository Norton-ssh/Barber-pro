# GUIA — COMO EDITAR A VIP BARBEARIA SEM VOLTAR AO CHAT

## 1) O arquivo principal de personalização é `config.py`
Você pode abrir esse arquivo e alterar:
- nome da loja
- descrição
- endereço
- telefone/WhatsApp
- Instagram
- horários de atendimento
- textos dos campos
- texto do agendamento público
- cores
- nome do arquivo da logo

Exemplo:
```python
STORE_NAME = "Barbearia do João"
STORE_DESCRIPTION = "Cortes masculinos e barba."
STORE_ADDRESS = "Rua X, 123 - Campo Novo do Parecis/MT"
STORE_PHONE = "(65) 99999-9999"
STORE_INSTAGRAM = "@barbeariadojoao"
```

## 2) Como trocar a logo
Coloque sua imagem na pasta `static/`.

Por exemplo:
`static/logo.png`

Depois, no `config.py`:
```python
LOGO_FILE = "logo.png"
SHOW_LOGO = True
```

Você pode substituir a imagem sempre que quiser.

## 3) Como alterar nomes de campos
No `config.py`, altere `FIELD_LABELS`.

Exemplo:
```python
"phone": "WhatsApp",
"notes": "Observações do cliente",
"price": "Valor do serviço",
```

## 4) Como alterar textos do agendamento público
No `config.py`:
```python
PUBLIC_BOOKING_TITLE = "Reserve seu horário"
PUBLIC_BOOKING_BUTTON = "Confirmar horário"
PUBLIC_BOOKING_DESCRIPTION = "Escolha seu barbeiro e horário."
```

## 5) Como publicar suas alterações
Depois de editar os arquivos:
1. Salve.
2. Envie/atualize os arquivos no GitHub.
3. Faça `Commit changes`.
4. O Render fará o novo deploy ou use `Manual Deploy -> Deploy latest commit`.

## 6) O que NÃO editar sem saber programação
- `app.py` (regras do sistema e banco)
- `render.yaml` (infraestrutura)
- `requirements.txt` (dependências)

Se quiser mudar somente aparência, marca, campos e textos, prefira `config.py` e os arquivos em `templates/`.

## 7) Banco de dados
O PostgreSQL do Render é separado do código. Alterar `config.py` ou HTML não apaga clientes/agendamentos.


## Permissões
- Administrador: acesso total, incluindo Configurações e Usuários.
- Colaborador Fixo: inserir, editar e excluir registros; não acessa Configurações.
- Colaborador Eventual: somente inserir novos registros; não pode editar, excluir, cancelar ou concluir.

## Despesas
Use o menu Despesas. Tipo Fixa + recorrente mantém a despesa como recorrente; Variável é lançada uma única vez. O dashboard e os relatórios descontam as despesas do resultado.
