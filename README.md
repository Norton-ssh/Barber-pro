# Barber Pro — Nível 2

Sistema funcional local para barbearia.

## Login inicial
E-mail: admin@barberpro.local
Senha: 123456

Troque a senha e a SECRET_KEY antes de produção.

## Recursos
- Login administrativo
- Dashboard
- Clientes
- Barbeiros e comissão
- Serviços
- Agenda com prevenção de conflito
- Conclusão de agendamento gerando venda
- Caixa
- Relatório por dia
- Comissão por barbeiro
- Serviços mais vendidos
- Área pública `/agendar` para clientes
- API de horários ocupados
- SQLite persistente

## Rodar
python -m pip install -r requirements.txt
python app.py

Abra http://localhost:5000
Área de agendamento do cliente: http://localhost:5000/agendar

## Produção
Para publicar na internet, usar servidor com HTTPS, PostgreSQL, senha com hash, backups e autenticação reforçada. WhatsApp requer integração com um provedor/API oficial.
