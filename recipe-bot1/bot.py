import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

from dotenv import load_dotenv
from telegram import Update, BotCommand, MenuButtonCommands
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

import db
import excel_export
import currency
from keyboards import main_menu, month_menu, currency_menu, MONTHS

load_dotenv()
import os
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

ASK_FIELD = 1
CUR_AMOUNT = 2
CUR_FROM = 3
CUR_TO = 4

WELCOME = (
    "👋 Здравствуйте! Я бот-анкета.\n\n"
    "Заполните свои данные — они сохранятся в базу данных SQLite3 "
    "и по запросу выгрузятся в Excel.\n\n"
    "💱 Также умею пересчитывать валюту:\n"
    "• /calc 100 USD RUB — конвертация\n"
    "• /rates — курсы валют"
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id)
    await update.message.reply_text(WELCOME, reply_markup=main_menu())


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "menu:main":
        await query.edit_message_text(WELCOME, reply_markup=main_menu())

    elif data == "menu:month":
        await query.edit_message_text(
            "📅 Выберите месяц рождения:", reply_markup=month_menu()
        )

    elif data.startswith("edit:"):
        field = data.split(":", 1)[1]
        context.user_data["editing_field"] = field
        prompts = {
            "first_name": "👤 Введите ваше имя:",
            "last_name": "✍️ Введите вашу фамилию:",
            "birth_year": "🎂 Введите год рождения (например, 1995):",
            "hobbies": "💼 Введите ваши увлечения или работу:",
        }
        await query.edit_message_text(prompts[field])
        return ASK_FIELD

    elif data.startswith("set_month:"):
        month_num = int(data.split(":", 1)[1])
        db.update_field(user_id, "birth_month", MONTHS[month_num - 1])
        await query.edit_message_text(
            f"✅ Месяц рождения сохранён: {MONTHS[month_num - 1]}",
            reply_markup=main_menu(),
        )

    elif data == "export":
        await query.edit_message_text("📊 Формирую Excel-файл...")
        try:
            path = excel_export.export_users_to_excel()
            with open(path, "rb") as f:
                await query.message.reply_document(
                    document=f,
                    filename=path.name,
                    caption="📊 Анкеты пользователей",
                )
            await query.message.reply_text(
                "Что-нибудь ещё?", reply_markup=main_menu()
            )
        except Exception as e:
            log.error(f"export error: {e}")
            await query.message.reply_text(f"Ошибка экспорта: {e}")

    return ConversationHandler.END


async def ask_field_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    field = context.user_data.get("editing_field")
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("Пожалуйста, введите текст.")
        return ASK_FIELD

    if field == "birth_year":
        if not (text.isdigit() and 1900 <= int(text) <= 2026):
            await update.message.reply_text(
                "⚠️ Введите корректный год (например, 1995)."
            )
            return ASK_FIELD

    db.update_field(update.effective_user.id, field, text)
    labels = {
        "first_name": "Имя",
        "last_name": "Фамилия",
        "birth_year": "Год рождения",
        "hobbies": "Увлечения / работа",
    }
    await update.message.reply_text(
        f"✅ {labels[field]} сохранено: {text}", reply_markup=main_menu()
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.", reply_markup=main_menu())
    return ConversationHandler.END


async def cmd_calc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.split()
    if len(parts) == 4:
        _, amount_str, cur_from, cur_to = parts
        try:
            amount = float(amount_str.replace(",", "."))
            converted, per_unit = await currency.convert(amount, cur_from, cur_to)
        except ValueError as e:
            await update.message.reply_text(f"⚠️ {e}")
            return ConversationHandler.END
        except RuntimeError as e:
            await update.message.reply_text(f"⚠️ Не удалось получить курсы: {e}")
            return ConversationHandler.END
        await update.message.reply_text(
            f"💱 {currency.fmt(amount)} {cur_from.upper()} = "
            f"<b>{currency.fmt(converted)} {cur_to.upper()}</b>\n\n"
            f"1 {cur_from.upper()} = {currency.fmt(per_unit, 4)} {cur_to.upper()}\n"
            f"1 {cur_to.upper()} = {currency.fmt(1 / per_unit, 4)} {cur_from.upper()}",
            parse_mode="HTML",
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "💱 Введите сумму, например: <b>100</b>", parse_mode="HTML"
    )
    return CUR_AMOUNT


async def calc_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "💱 Введите сумму, например: <b>100</b>", parse_mode="HTML"
    )
    return CUR_AMOUNT


async def cur_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(",", ".")
    try:
        amount = float(text)
    except ValueError:
        await update.message.reply_text("⚠️ Введите сумму числом:")
        return CUR_AMOUNT
    if amount < 0:
        await update.message.reply_text("⚠️ Сумма не может быть отрицательной:")
        return CUR_AMOUNT
    context.user_data["cur_amount"] = amount
    await update.message.reply_text(
        "💰 <b>Из какой валюты?</b>",
        parse_mode="HTML",
        reply_markup=currency_menu("calc:from"),
    )
    return CUR_FROM


async def cur_from(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "menu:main":
        await query.edit_message_text(WELCOME, reply_markup=main_menu())
        return ConversationHandler.END
    context.user_data["cur_from"] = query.data.split(":")[-1]
    await query.edit_message_text(
        "💱 <b>В какую валюту?</b>",
        parse_mode="HTML",
        reply_markup=currency_menu("calc:to"),
    )
    return CUR_TO


async def cur_to(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "menu:main":
        await query.edit_message_text(WELCOME, reply_markup=main_menu())
        return ConversationHandler.END
    cur = query.data.split(":")[-1]
    amount = context.user_data["cur_amount"]
    cur_from = context.user_data["cur_from"]
    try:
        converted, per_unit = await currency.convert(amount, cur_from, cur)
    except Exception as e:
        log.error(f"convert error: {e}")
        await query.edit_message_text(
            "⚠️ Не удалось получить курсы. Попробуйте позже.",
            reply_markup=main_menu(),
        )
        return ConversationHandler.END
    await query.edit_message_text(
        f"💱 {currency.fmt(amount)} {cur_from} = "
        f"<b>{currency.fmt(converted)} {cur}</b>\n\n"
        f"1 {cur_from} = {currency.fmt(per_unit, 4)} {cur}\n"
        f"1 {cur} = {currency.fmt(1 / per_unit, 4)} {cur_from}",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )
    return ConversationHandler.END


async def rates_show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        rates = await currency.popular_rates("RUB")
    except Exception as e:
        log.error(f"rates error: {e}")
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                "⚠️ Не удалось получить курсы. Попробуйте позже."
            )
        else:
            await update.message.reply_text(
                "⚠️ Не удалось получить курсы. Попробуйте позже."
            )
        return ConversationHandler.END

    lines = ["📈 <b>Курсы к RUB:</b>", ""]
    for code, value in rates:
        lines.append(f"1 {code} = {currency.fmt(value)} RUB")
    text = "\n".join(lines)

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=main_menu())
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=main_menu())
    return ConversationHandler.END


def main():
    db.init_db()
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(menu_handler, pattern="^(menu:|edit:|set_month:|export)"),
            CallbackQueryHandler(calc_start, pattern="^calc:start$"),
            CallbackQueryHandler(rates_show, pattern="^rates:show$"),
            CommandHandler("calc", cmd_calc),
            CommandHandler("rates", rates_show),
        ],
        states={
            ASK_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_field_text)],
            CUR_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, cur_amount)],
            CUR_FROM: [CallbackQueryHandler(cur_from, pattern="^(calc:from:|menu:main)")],
            CUR_TO: [CallbackQueryHandler(cur_to, pattern="^(calc:to:|menu:main)")],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(menu_handler, pattern="^menu:main$"),
        ],
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(conv)

    import asyncio

    async def setup():
        await app.initialize()
        await app.bot.set_my_commands([
            BotCommand("start", "Открыть меню анкеты"),
            BotCommand("calc", "Конвертация валют: /calc 100 USD RUB"),
            BotCommand("rates", "Курсы валют"),
            BotCommand("cancel", "Отменить ввод"),
        ])
        await app.bot.set_chat_menu_button(menu_button=MenuButtonCommands())

    loop = asyncio.new_event_loop()
    loop.run_until_complete(setup())
    loop.run_until_complete(app.shutdown())
    loop.close()

    webhook_url = os.getenv("WEBHOOK_URL", "").strip()
    port = int(os.getenv("PORT", "8080"))

    if webhook_url:
        log.info("Бот запущен через webhook: %s", webhook_url)
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=TOKEN,
            webhook_url=f"{webhook_url}/{TOKEN}",
        )
    else:
        log.info("Бот запущен! (polling)")
        app.run_polling()


if __name__ == "__main__":
    main()
