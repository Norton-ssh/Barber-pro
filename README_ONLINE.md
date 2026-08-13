# VIP Barbearia — versão online

Projeto preparado para Render + PostgreSQL.

## Publicação
1. Envie os arquivos do projeto para o repositório GitHub `Barber-pro`.
2. No Render, conecte o GitHub e crie um Blueprint/Web Service a partir do repositório.
3. O `render.yaml` já define:
   - Web Service `vip-barbearia`
   - PostgreSQL `vip-barbearia-db`
   - `DATABASE_URL`
   - `SECRET_KEY`
   - Gunicorn
4. Depois do deploy, abra a URL `*.onrender.com`.

## Login inicial
E-mail: admin@vipbarbearia.com
Senha: 123456

Troque a senha assim que o sistema estiver acessível. Esta versão ainda usa senha em texto simples; antes de uso comercial devemos migrar para hash de senha e adicionar recuperação de senha.

## Observação sobre o plano gratuito
O Render informa que bancos Postgres gratuitos têm validade limitada (30 dias). Para operação contínua, selecione um plano pago antes de expirar.

## Marca
Nome: VIP Barbearia

## Desenvolvimento local
Se `DATABASE_URL` não existir, o app continua usando SQLite localmente.
