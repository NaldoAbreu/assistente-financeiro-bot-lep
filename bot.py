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
        "• `/resumo`\n"
        "• `/buscar <descrição>` para encontrar transações específicas\n"
        "• `/buscar <data_inicial> <data_final>` para filtrar por período\n\n"
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

    transacoes_ordenadas = sorted(transacoes, key=lambda x: x["data"], reverse=True)
    for t in transacoes_ordenadas[:10]:  # Mostra apenas as últimas 10 transações
        icone = "💵" if t["tipo"] == "entrada" else "💸"
        relatorio += f"{icone} ID {t['id']}: {t['descricao']} - R$ {t['valor']:.2f} em {t['data'].strftime('%d/%m/%Y %H:%M')}\n"

    update.message.reply_text(relatorio, parse_mode='Markdown')

def buscar_transacao(update: Update, context: CallbackContext):
    args = context.args
    if not args:
        update.message.reply_text(
            "🔍 Use `/buscar <descrição>` para buscar por nome.\n"
            "📅 Ou use `/buscar <data_inicial> <data_final>` (Ex.: `/buscar 01/02/2024 10/02/2024`).",
            parse_mode='Markdown'
        )
        return

    filtro = " ".join(args)
    
    if len(args) == 2:
        try:
            data_inicio = datetime.strptime(args[0], "%d/%m/%Y")
            data_fim = datetime.strptime(args[1], "%d/%m/%Y") + timedelta(days=1) - timedelta(seconds=1)
        except ValueError:
            update.message.reply_text("❌ Formato de data inválido! Use: `/buscar 01/02/2024 10/02/2024`.", parse_mode='Markdown')
            return

        transacoes_filtradas = [t for t in transacoes if data_inicio <= t["data"] <= data_fim]
        periodo = f"entre {data_inicio.strftime('%d/%m/%Y')} e {data_fim.strftime('%d/%m/%Y')}"

    else:
        transacoes_filtradas = [t for t in transacoes if filtro.lower() in t["descricao"].lower()]
        periodo = f"contendo '{filtro}'"

    if not transacoes_filtradas:
        update.message.reply_text(f"❌ Nenhuma transação encontrada {periodo}.", parse_mode='Markdown')
        return

    relatorio = f"🔍 *Resultados da busca {periodo}:*\n\n"
    for t in transacoes_filtradas:
        icone = "💵" if t["tipo"] == "entrada" else "💸"
        relatorio += f"{icone} ID {t['id']}: {t['descricao']} - R$ {t['valor']:.2f} em {t['data'].strftime('%d/%m/%Y %H:%M')}\n"

    update.message.reply_text(relatorio, parse_mode='Markdown')

# Registrando os comandos
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("entrada", registrar_entrada))
dispatcher.add_handler(CommandHandler("gasto", registrar_gasto))
dispatcher.add_handler(CommandHandler("resumo", resumo))
dispatcher.add_handler(CommandHandler("buscar", buscar_transacao))

@app.route("/", methods=["GET"])
def home():
    return "Bot está rodando!", 200

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()
    update = Update.de_json(data, bot)
    dispatcher.process_update(update)
    return "OK", 200

def set_webhook():
    bot.set_webhook(url=f"{WEBHOOK_URL}{TOKEN}")

@app.before_first_request
def init_webhook():
    set_webhook()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8443))
    app.run(host="0.0.0.0", port=port)
