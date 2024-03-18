from src.utils import (search_vacancies, get_user_action, handle_action, create_database,
                       fill_database_with_companies_and_vacancies, check_database_exists)
from src.db_manager import DBManager


def welcome_message():
    """
    Приветствует пользователя и кратко объясняет, что это за приложение.
    """
    print("Добро пожаловать в наше приложение для поиска вакансий на hh.ru!")
    print("Это приложение поможет вам найти интересные вакансии "
          "и сохранить их в вашу персональную базу данных.")
    print()


def query_first_time_user():
    """
    Запрашивает у пользователя, впервые ли он использует приложение.
    Возвращает True, если пользователь новый, и False, если нет.
    """
    while True:
        response = input("Вы здесь впервые? (да/нет): ").strip().lower()
        if response == "да":
            return True
        elif response == "нет":
            return False
        else:
            print("Пожалуйста, введите 'да' или 'нет'.")


def exit_application():
    """
    Завершает приложение с прощальным сообщением.
    """
    print("Спасибо за использование нашего приложения! До свидания.")


def new_user_actions():
    """
    Предлагает новым пользователям выбрать действие.
    """
    while True:
        print("Выберите действие:\n1 - Найти вакансии по ключевому слову\n2 - Выйти")
        choice = input("Ваш выбор: ").strip()
        if choice == "1":
            search_vacancies()
            database_name = input("Введите имя базы данных для сохранения вакансий: ")
            create_database(database_name)
            db_manager = DBManager(database_name)
            fill_database_with_companies_and_vacancies(database_name)
            return db_manager  # Возвращаем экземпляр менеджера базы данных
        elif choice == "2":
            exit_application()
            return None  # Выход из приложения, возвращаем None
        else:
            print("Неверный ввод. Пожалуйста, выберите действие: 1 или 2")


def returning_user_actions():
    """
    Предлагает возвращающимся пользователям выбрать действие.
    Возвращает экземпляр DBManager для работы с базой данных.
    """
    print("Выберите действие:\n1. Работать с уже созданной базой данных\n"
          "2. Создать новую базу данных\n3. Выйти")
    choice = input("Ваш выбор: ").strip()
    if choice == "1":
        db_name = input("Введите имя базы данных: ")
        if not check_database_exists(db_name):
            print(f"База данных с именем '{db_name}' не существует.")
            return returning_user_actions()
        else:
            return DBManager(db_name)

    elif choice == "2":
        print("Отлично! Давайте приступим к созданию новой базы данных и заполнению её данными.")
        return new_user_actions()  # Запуск действий новичка для создания новой базы данных

    elif choice == "3":
        exit_application()
        return None  # Выход из приложения, возвращаем None
    else:
        print("Неверный ввод. Попробуйте еще раз.")
        return returning_user_actions()  # Рекурсивный вызов функции для правильного выбора действия


def main():
    """
    Основная функция приложения.
    """
    welcome_message()
    db_manager = None  # Инициализация переменной для дальнейшего использования

    if query_first_time_user():
        print()
        print("Мы рады приветствовать новых пользователей! Давайте начнём.")
        print()
        db_manager = new_user_actions()  # Обработка действий нового пользователя
    else:
        print()
        print("Добро пожаловать обратно! Что бы вы хотели сделать сегодня?")
        print()
        db_manager = returning_user_actions()  # Получаем экземпляр DBManager
        # от возвращающегося пользователя

    # Предлагаем пользователю действия с базой данных
    while db_manager:
        action = get_user_action()
        if action == "6":
            print()
            exit_application()
            break
        elif action in ["1", "2", "3", "4", "5"]:
            handle_action(action, db_manager)
        else:
            print("Неверный ввод. Попробуйте еще раз.")

    if db_manager:
        db_manager.close()


if __name__ == "__main__":
    main()
