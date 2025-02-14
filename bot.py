import logging
import os
from threading import Thread
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext
from datetime import datetime, timedelta

# Configuração do log
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Token do bot e URL do Render
TOKEN = "8179383930:AAFOkb050TIkrG3Ko7lWgIbBWMQ2yHEN4sA"
WEBHOOK_URL = "https://assistente-financeiro-bot-lep-1.onrender.com"  # Substitua pelo seu URL

bot = Bot(TOKEN)
app = Flask(__name__)

# Configuração do Dispatcher
dispatcher = Dispatcher(bot, None, use_context=True)

# Dicionário para armazenar os gastos
gastos = []

# --- Funções do bot ---
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Olá! Sou o Assistente Financeiro.\n"
        "Envie um gasto no formato: 'nome_do_item valor'\n"
        "Exemplo: 'camiseta 125'\n\n"
        "Para obter um relatório, envie:\n"
        "- 'me envie os gastos diários'\n"
        "- 'me envie os gastos semanais'\n"
        "- 'me envie os gastos mensais'"
    )

def registrar_gasto(update: Update, context: CallbackContext):
    text = update.message.text.strip()
    partes = text.rsplit(" ", 1)  # Divide pelo último espaço
    
    if len(partes) != 2 or not partes[1].isdigit():
        update.message.reply_text("Formato inválido! Envie no formato: 'item valor' (Exemplo: 'camiseta 125')")
        return
    
    item, valor = partes[0], int(partes[1])
    data = datetime.now()
    gastos.append({"item": item, "valor": valor, "data": data})
    update.message.reply_text(f"Gasto registrado: {item} - R$ {valor}")

def gerar_relatorio(update: Update, periodo: str):
    agora = datetime.now()
    if periodo == "diário":
        inicio = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    elif periodo == "semanal":
        inicio = agora - timedelta(days=agora.weekday())
    elif periodo == "mensal":
        inicio = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        update.message.reply_text("Período inválido!")
        return
    
    gastos_filtrados = [g for g in gastos if g['data'] >= inicio]
    if not gastos_filtrados:
        update.message.reply_text(f"Nenhum gasto registrado para o período {periodo}.")
        return
    
    total = sum(g["valor"] for g in gastos_filtrados)
    relatorio = f"Gastos {periodo}:\n"
    relatorio += "\n".join([f"{g['item']} - R$ {g['valor']}" for g in gastos_filtrados])
    relatorio += f"\nTotal: R$ {total}"
    update.message.reply_text(relatorio)

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

# Adiciona os handlers ao Dispatcher
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, interpretar_mensagem))

# --- Configuração do Flask ---
@app.route("/", methods=["GET"])
def home():
    return "Bot está rodando!", 200

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(), bot)
    dispatcher.process_update(update)
    return "OK", 200

def set_webhook():
    bot.set_webhook(url=WEBHOOK_URL + TOKEN)

if __name__ == "__main__":
    set_webhook()  # Define o webhook no Telegram
    port = int(os.environ.get("PORT", 8443))
    app.run(host="0.0.0.0", port=port)
