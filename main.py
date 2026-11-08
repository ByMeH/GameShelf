import math
import sqlite3

from database import GameDatabase


STATUSES = ("В планах", "Играю", "Пройдена", "Брошена")
SORT_OPTIONS = {
    "1": ("id", "ID"),
    "2": ("title", "названию"),
    "3": ("platform", "платформе"),
    "4": ("genre", "жанру"),
    "5": ("release_year", "году выпуска"),
    "6": ("hours_played", "часам"),
    "7": ("rating", "рейтингу"),
}


def read_nonempty(prompt: str, default: str | None = None) -> str:
    while True:
        value = input(prompt).strip()
        if not value and default is not None:
            return default
        if value:
            return value
        print("Поле не должно быть пустым.")


def read_optional_int(prompt: str, minimum: int, maximum: int) -> int | None:
    while True:
        value = input(prompt).strip()
        if not value:
            return None
        try:
            number = int(value)
        except ValueError:
            print("Введите целое число или оставьте поле пустым.")
            continue
        if minimum <= number <= maximum:
            return number
        print(f"Допустимый диапазон: {minimum}–{maximum}.")


def read_float(prompt: str, default: float = 0.0) -> float:
    while True:
        value = input(prompt).strip().replace(",", ".")
        if not value:
            return default
        try:
            number = float(value)
        except ValueError:
            print("Введите число, например 12.5.")
            continue
        if number >= 0:
            return number
        print("Число не может быть отрицательным.")


def read_status(default: str = "В планах") -> str:
    print("Статус:")
    for index, status in enumerate(STATUSES, start=1):
        print(f"  {index}. {status}")
    while True:
        value = input(f"Выбор [1-4, Enter — {default}]: ").strip()
        if not value:
            return default
        if value in ("1", "2", "3", "4"):
            return STATUSES[int(value) - 1]
        print("Выберите номер от 1 до 4.")


def collect_game_data(existing: sqlite3.Row | None = None) -> tuple:
    def current(field: str) -> str:
        if existing is None or existing[field] is None:
            return ""
        return str(existing[field])

    title = read_nonempty(f"Название [{current('title')}]: ", current("title") or None)
    platform = read_nonempty(
        f"Платформа [{current('platform')}]: ", current("platform") or None
    )
    genre = read_nonempty(f"Жанр [{current('genre')}]: ", current("genre") or None)

    year_default = current("release_year")
    year = read_optional_int(
        f"Год выпуска [{year_default or 'не указан'}]: ", 1952, 2026
    )
    if year is None and year_default:
        year = int(year_default)

    status = read_status(existing["status"] if existing else "В планах")

    hours_default = float(existing["hours_played"]) if existing else 0.0
    hours_text = input(f"Часов наиграно [{hours_default}]: ").strip()
    if hours_text:
        try:
            hours = float(hours_text.replace(",", "."))
            if not math.isfinite(hours) or hours < 0:
                raise ValueError
        except ValueError:
            print("Некорректное количество часов. Используется прежнее значение.")
            hours = hours_default
    else:
        hours = hours_default

    rating_default = current("rating")
    rating = read_optional_int(
        f"Оценка 1–10 [{rating_default or 'не указана'}]: ", 1, 10
    )
    if rating is None and rating_default:
        rating = int(rating_default)

    return title, platform, genre, year, status, hours, rating


def shorten(value: object, width: int) -> str:
    text = "—" if value is None else str(value)
    if len(text) > width:
        return text[: width - 1] + "…"
    return text


def show_games(rows: list[sqlite3.Row], heading: str) -> None:
    print(f"\n{heading}")
    if not rows:
        print("Записей не найдено.")
        return

    columns = (
        ("ID", 4),
        ("Название", 23),
        ("Платформа", 13),
        ("Жанр", 13),
        ("Год", 6),
        ("Статус", 12),
        ("Часы", 7),
        ("Оценка", 7),
    )
    separator = "+".join("-" * (width + 2) for _, width in columns)
    print("+" + separator + "+")
    print("|" + "|".join(f" {name:<{width}} " for name, width in columns) + "|")
    print("+" + separator + "+")

    for row in rows:
        values = (
            row["id"], row["title"], row["platform"], row["genre"],
            row["release_year"], row["status"], row["hours_played"],
            row["rating"],
        )
        cells = [shorten(value, width) for value, (_, width) in zip(values, columns)]
        print("|" + "|".join(
            f" {cell:<{width}} " for cell, (_, width) in zip(cells, columns)
        ) + "|")
    print("+" + separator + "+")
    print(f"Всего записей: {len(rows)}")


def read_id() -> int:
    while True:
        try:
            value = int(input("ID игры: "))
            if value > 0:
                return value
        except ValueError:
            pass
        print("Введите положительное целое число.")


def print_menu() -> None:
    print("""
========== GAMESHELF ==========
1. Показать игровую коллекцию
2. Добавить игру
3. Найти игру
4. Отсортировать коллекцию
5. Редактировать игру
6. Переместить игру в архив
7. Показать архив
8. Восстановить игру
9. Удалить игру навсегда
10. Статистика
0. Выход
===============================
""")


def run() -> None:
    database = GameDatabase()
    print(f"База данных: {database.db_path.resolve()}")
    print("GameShelf запущен. Данные сохраняются между запусками.")

    try:
        while True:
            print_menu()
            choice = input("Выберите действие: ").strip()

            try:
                if choice == "1":
                    show_games(database.list_games(), "АКТИВНАЯ КОЛЛЕКЦИЯ")

                elif choice == "2":
                    print("\nДобавление игры")
                    data = collect_game_data()
                    game_id = database.add_game(*data)
                    print(f"Игра добавлена. Её ID: {game_id}")

                elif choice == "3":
                    query = read_nonempty("Поиск по названию, платформе или жанру: ")
                    rows = database.list_games(search=query)
                    show_games(rows, f"РЕЗУЛЬТАТЫ ПОИСКА: {query}")

                elif choice == "4":
                    print("Сортировать по:")
                    for key, (_, label) in SORT_OPTIONS.items():
                        print(f"  {key}. {label}")
                    sort_choice = input("Ваш выбор: ").strip()
                    if sort_choice not in SORT_OPTIONS:
                        print("Неизвестный вариант сортировки.")
                        continue
                    direction = input("По убыванию? (д/н): ").strip().lower()
                    sort_by, label = SORT_OPTIONS[sort_choice]
                    rows = database.list_games(
                        sort_by=sort_by, descending=direction in ("д", "да", "y", "yes")
                    )
                    show_games(rows, f"СОРТИРОВКА ПО {label.upper()}")

                elif choice == "5":
                    show_games(database.list_games(), "АКТИВНАЯ КОЛЛЕКЦИЯ")
                    game_id = read_id()
                    game = database.get_game(game_id)
                    if game is None or game["is_deleted"]:
                        print("Активная игра с таким ID не найдена.")
                        continue
                    print("Введите новые значения. Enter оставляет прежнее значение.")
                    data = collect_game_data(game)
                    if database.update_game(game_id, *data):
                        print("Запись обновлена.")
                    else:
                        print("Не удалось обновить запись.")

                elif choice == "6":
                    show_games(database.list_games(), "АКТИВНАЯ КОЛЛЕКЦИЯ")
                    game_id = read_id()
                    if database.archive_game(game_id):
                        print("Игра перемещена в архив.")
                    else:
                        print("Активная игра с таким ID не найдена.")

                elif choice == "7":
                    show_games(database.list_games(archived=True), "АРХИВ")

                elif choice == "8":
                    show_games(database.list_games(archived=True), "АРХИВ")
                    game_id = read_id()
                    if database.restore_game(game_id):
                        print("Игра восстановлена.")
                    else:
                        print("Игра с таким ID в архиве не найдена.")

                elif choice == "9":
                    show_games(database.list_games(archived=True), "АРХИВ")
                    game_id = read_id()
                    confirmation = input(
                        "Физически удалить эту запись? Введите ДА для подтверждения: "
                    ).strip().lower()
                    if confirmation == "да":
                        if database.hard_delete_game(game_id):
                            print("Запись физически удалена из базы данных.")
                        else:
                            print("Запись не найдена в архиве.")
                    else:
                        print("Удаление отменено.")

                elif choice == "10":
                    stats = database.get_statistics()
                    print("\nСТАТИСТИКА АКТИВНОЙ КОЛЛЕКЦИИ")
                    print(f"Игр в коллекции: {stats['total_games']}")
                    print(f"Пройдено игр: {stats['completed'] or 0}")
                    print(f"Игр с оценкой: {stats['rated_games']}")
                    print(f"Средняя оценка: {stats['average_rating'] or 0}")
                    print(f"Всего наиграно часов: {stats['total_hours']}")

                elif choice == "0":
                    print("Работа GameShelf завершена. До встречи!")
                    break

                else:
                    print("Неизвестная команда. Выберите пункт от 0 до 10.")

            except sqlite3.Error as error:
                print(f"Ошибка базы данных: {error}")

            input("\nНажмите Enter, чтобы вернуться в меню...")

    except (KeyboardInterrupt, EOFError):
        print("\nПолучен сигнал завершения.")
    finally:
        database.close()
        print("Соединение с базой данных закрыто.")


if __name__ == "__main__":
    run()
