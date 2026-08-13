# ============================================================
# CONFIGURAÇÃO EDITÁVEL DA VIP BARBEARIA
# ------------------------------------------------------------
# Você pode editar este arquivo diretamente no VS Code,
# Bloco de Notas ou outro editor de texto.
# Depois de salvar e publicar no GitHub, o Render atualizará o site.
# ============================================================

APP_VERSION = "VIP Barbearia 2.0.0 — Permissões + Despesas"

# DADOS DA LOJA
STORE_NAME = "VIP Barbearia"
STORE_DESCRIPTION = "Cortes, barba e cuidados masculinos com atendimento profissional."
STORE_ADDRESS = "Campo Novo do Parecis - MT"
STORE_PHONE = "(65) 99999-9999"
STORE_WHATSAPP = "5565996002369"  # somente números, com DDI e DDD
WHATSAPP_LINK = "https://wa.me/5565996002369?text=Ol%C3%A1%20tudo%20bem%3F"
PIX_KEY = "65996002369"
PIX_NAME = "VIP Barbearia"
PAYMENT_NOTE = "Após o agendamento, você pode enviar o comprovante pelo WhatsApp."
STORE_INSTAGRAM = "@vipbarbearia"

# LOGO
# Coloque seu arquivo em: static/logo.png
# Pode usar PNG/JPG/SVG. Para SVG, altere para "logo.svg".
LOGO_FILE = "logo.svg"
SHOW_LOGO = True

# CORES DO SISTEMA
PRIMARY_COLOR = "#c69a45"
DARK_COLOR = "#151515"
BACKGROUND_COLOR = "#f5f5f5"

# HORÁRIO DE ATENDIMENTO (usado como informação pública)
OPENING_HOURS = [
    "Segunda a sexta: 08:00 às 19:00",
    "Sábado: 08:00 às 18:00",
    "Domingo: Fechado",
]

# TEXTOS EDITÁVEIS DOS CAMPOS
FIELD_LABELS = {
    "client_name": "Nome do cliente",
    "phone": "Telefone / WhatsApp",
    "email": "E-mail",
    "birthday": "Data de aniversário",
    "notes": "Observações",
    "barber_name": "Nome do barbeiro",
    "commission": "Comissão (%)",
    "service_name": "Nome do serviço",
    "duration": "Duração (minutos)",
    "price": "Preço",
    "appointment_date": "Data",
    "appointment_time": "Horário",
    "payment": "Forma de pagamento",
}

# TEXTOS DE TELA
PUBLIC_BOOKING_TITLE = "Agende seu horário"
PUBLIC_BOOKING_BUTTON = "Solicitar agendamento"
PUBLIC_BOOKING_DESCRIPTION = "Escolha seu serviço, barbeiro, data e horário."
LOGIN_SUBTITLE = "Entrar no painel administrativo"

APP_VERSION = "2.0.1 - Permissões + Despesas (PostgreSQL corrigido)"
