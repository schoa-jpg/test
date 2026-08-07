from telegram import InlineKeyboardButton, InlineKeyboardMarkup

MONTHS = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]


def main_menu() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("1. Ваше имя", callback_data="edit:first_name")],
        [InlineKeyboardButton("2. Фамилия", callback_data="edit:last_name")],
        [InlineKeyboardButton("3. Год рождения", callback_data="edit:birth_year")],
        [InlineKeyboardButton("4. Месяц рождения", callback_data="menu:month")],
        [InlineKeyboardButton("5. Увлечения или работа", callback_data="edit:hobbies")],
        [InlineKeyboardButton("6. Выгрузить в Excel", callback_data="export")],
    ]
    return InlineKeyboardMarkup(buttons)


def month_menu() -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, 12, 3):
        row = [
            InlineKeyboardButton(MONTHS[j], callback_data=f"set_month:{j + 1}")
            for j in range(i, min(i + 3, 12))
        ]
        rows.append(row)
    rows.append([InlineKeyboardButton("◀ В меню", callback_data="menu:main")])
    return InlineKeyboardMarkup(rows)
