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
from keyboards import main_menu, month_menu, MONTHS

load_dotenv()
import os
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

ASK_FIELD = 1

WELCOME = (
    "👋 Здравствуйте! Я бот-анкета.\n\n"
    "Заполните свои данные — они сохранятся в базу данных SQLite3 "
    "и по запросу выгрузятся в Excel."
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


def main():
    db.init_db()
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(menu_handler, pattern="^(menu:|edit:|set_month:|export)")],
        states={
            ASK_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_field_text)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CallbackQueryHandler(menu_handler, pattern="^menu:main$")],
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(conv)

    import asyncio

    async def setup():
        await app.initialize()
        await app.bot.set_my_commands([
            BotCommand("start", "Открыть меню анкеты"),
            BotCommand("cancel", "Отменить ввод"),
        ])
        await app.bot.set_chat_menu_button(menu_button=MenuButtonCommands())

    loop = asyncio.new_event_loop()
    loop.run_until_complete(setup())
    loop.run_until_complete(app.shutdown())
    loop.close()

    log.info("Бот запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
