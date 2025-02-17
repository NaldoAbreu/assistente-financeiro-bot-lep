import logging
import os
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext
from datetime import datetime, timedelta

# Configuração do log
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Token do bot e URL do Render
TOKEN = "8179383930:AAFOkb050TIkrG3Ko7lWgIbBWMQ2yHEN4sA"
WEBHOOK_URL = "https://assistente-financeiro-bot-lep-1.onrender.com/"

bot = Bot(TOKEN)
app = Flask(__name__)

dispatcher = Dispatcher(bot, None, use_context=True)

# Lista para armazenar os gastos (em memória)
gastos = []

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Olá! Sou o Assistente Financeiro 🤖.\n\n"
        "Envie um gasto no formato: `nome_do_item valor`\n"
        "Exemplo: `camiseta 125,50`\n\n"
        "Para obter um relatório, envie:\n"
        "- `me envie os gastos diários`\n"
        "- `me envie os gastos semanais`\n"
        "- `me envie os gastos mensais`",
        parse_mode='Markdown'
    )

def registrar_gasto(update: Update, context: CallbackContext):
    text = update.message.text.strip()
    partes = text.rsplit(" ", 1)  # Divide pelo último espaço
    
    if len(partes) != 2:
        update.message.reply_text(
            "❌ Formato inválido! Use: `item valor` (Ex.: `camiseta 125,50`)",
            parse_mode='Markdown'
        )
        return

    item = partes[0]
    # Permite valores com vírgula ou ponto
    valor_str = partes[1].replace(',', '.')
    try:
        valor = float(valor_str)
    except ValueError:
        update.message.reply_text(
            "❌ Valor inválido! Certifique-se de usar números (Ex.: `125,50`)",
            parse_mode='Markdown'
        )
        return

    data = datetime.now()
    gastos.append({"item": item, "valor": valor, "data": data})
    update.message.reply_text(
        f"📌 Gasto registrado: *{item}* - R$ {valor:.2f} em {data.strftime('%d/%m/%Y %H:%M:%S')}",
        parse_mode='Markdown'
    )

def gerar_relatorio(update: Update, periodo: str):
    agora = datetime.now()
    if periodo == "diário":
        inicio = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    elif periodo == "semanal":
        inicio = agora - timedelta(days=agora.weekday())
        inicio = inicio.replace(hour=0, minute=0, second=0, microsecond=0)
    elif periodo == "mensal":
        inicio = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        update.message.reply_text("❌ Período inválido!")
        return

    gastos_filtrados = [g for g in gastos if g["data"] >= inicio]
    if not gastos_filtrados:
        update.message.reply_text(f"❌ Nenhum gasto registrado para o período {periodo}.")
        return

    total = sum(g["valor"] for g in gastos_filtrados)
    relatorio = f"📝 *Gastos {periodo.capitalize()}:*\n\n"
    for g in gastos_filtrados:
        relatorio += f"📌 {g['item']} - R$ {g['valor']:.2f} em {g['data'].strftime('%d/%m/%Y %H:%M:%S')}\n"
    relatorio += f"\n💰 *Total: R$ {total:.2f}*"
    update.message.reply_text(relatorio, parse_mode='Markdown')

def interpretar_mensagem(update: Update, context: CallbackContext):
    text = update.message.text.lower()
    if "gastos diários" in text:
        gerar_relatorio(update, "diário")
    elif "gastos semanais" in text:
        gerar_relatorio(update, "semanal")
    elif "gastos mensais" in text:
        gerar_relatorio(update, "mensal")
    else:
        registrar_gasto(update, context)

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, interpretar_mensagem))

@app.route("/", methods=["GET"])
def home():
    return "Bot está rodando!", 200

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        logger.info(f"Recebido webhook: {data}")
        update = Update.de_json(data, bot)
        dispatcher.process_update(update)
    except Exception as e:
        logger.error(f"Erro no processamento da mensagem: {e}")
    return "OK", 200

def set_webhook():
    webhook_url = f"{WEBHOOK_URL}{TOKEN}"
    success = bot.set_webhook(url=webhook_url)
    if success:
        logger.info(f"Webhook configurado com sucesso: {webhook_url}")
    else:
        logger.error("Falha ao configurar webhook!")

@app.before_first_request
def init_webhook():
    set_webhook()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8443))
    app.run(host="0.0.0.0", port=port)

