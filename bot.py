import logging
import os
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, CallbackContext
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

# Lista para armazenar as transações e variável para gerar IDs
transacoes = []
proximo_id = 1

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Olá! Sou o Assistente Financeiro 🤖.\n\n"
        "Use os comandos abaixo para registrar suas transações:\n"
        "• `/entrada <descrição> <valor>` para registrar uma receita (Ex.: `/entrada Salário 2000,00`)\n"
        "• `/gasto <descrição> <valor>` para registrar uma despesa (Ex.: `/gasto Aluguel 800,00`)\n\n"
        "Para visualizar seu resumo financeiro, use:\n"
        "• `/resumo`\n\n"
        "Obs.: O valor pode ser informado com vírgula ou ponto.",
        parse_mode='Markdown'
    )

def registrar_transacao(update: Update, context: CallbackContext, tipo: str):
    global proximo_id
    args = context.args
    if len(args) < 2:
        update.message.reply_text(
            f"❌ Formato inválido! Use: `/{tipo} <descrição> <valor>` (Ex.: `/{tipo} Internet 99,90`)",
            parse_mode='Markdown'
        )
        return

    descricao = " ".join(args[:-1])
    valor_str = args[-1].replace(',', '.')
    try:
        valor = float(valor_str)
    except ValueError:
        update.message.reply_text(
            "❌ Valor inválido! Certifique-se de usar números (Ex.: `99,90`)",
            parse_mode='Markdown'
        )
        return

    data = datetime.now()
    transacao = {
        "id": proximo_id,
        "tipo": tipo,
        "descricao": descricao,
        "valor": valor,
        "data": data
    }
    transacoes.append(transacao)
    proximo_id += 1

    emoji = "💵" if tipo == "entrada" else "💸"
    update.message.reply_text(
        f"{emoji} Transação registrada (ID {transacao['id']}): *{descricao}* - R$ {valor:.2f} em {data.strftime('%d/%m/%Y %H:%M')}",
        parse_mode='Markdown'
    )

def registrar_entrada(update: Update, context: CallbackContext):
    registrar_transacao(update, context, tipo="entrada")

def registrar_gasto(update: Update, context: CallbackContext):
    registrar_transacao(update, context, tipo="gasto")

def resumo(update: Update, context: CallbackContext):
    if not transacoes:
        update.message.reply_text("❌ Não há transações registradas.")
        return

    total_entradas = sum(t["valor"] for t in transacoes if t["tipo"] == "entrada")
    total_gastos = sum(t["valor"] for t in transacoes if t["tipo"] == "gasto")
    saldo = total_entradas - total_gastos

    relatorio = "📝 *Resumo Financeiro:*\n\n"
    relatorio += f"💵 Total de entradas: R$ {total_entradas:.2f}\n"
    relatorio += f"💸 Total de gastos: R$ {total_gastos:.2f}\n"
    relatorio += f"💰 Saldo final: R$ {saldo:.2f}\n\n"
    relatorio += "*Transações:*\n"

    # Ordena as transações por data (mais recentes primeiro)
    transacoes_ordenadas = sorted(transacoes, key=lambda x: x["data"], reverse=True)
    for t in transacoes_ordenadas:
        icone = "💵" if t["tipo"] == "entrada" else "💸"
        relatorio += f"{icone} ID {t['id']}: {t['descricao']} - R$ {t['valor']:.2f} em {t['data'].strftime('%d/%m/%Y %H:%M')}\n"

    update.message.reply_text(relatorio, parse_mode='Markdown')

# Registrando os comandos
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("entrada", registrar_entrada))
dispatcher.add_handler(CommandHandler("gasto", registrar_gasto))
dispatcher.add_handler(CommandHandler("resumo", resumo))

# Endpoint para verificação simples
@app.route("/", methods=["GET"])
def home():
    return "Bot está rodando!", 200

# Webhook para receber atualizações do Telegram
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
