import json
from .api import HeadHunterAPI
import os
import psycopg2
from .config import config
from .db_manager import DBManager
from datetime import datetime


def search_vacancies():
    """
    Запрашивает у пользователя поисковое слово и город, выводит список вакансий с уникальными компаниями,
    и просит пользователя выбрать до 10 компаний для сохранения.
    """
    api = HeadHunterAPI()
    search_query = input("Введите ключевое слово для поиска вакансий: ").strip()
    city = input("Введите название города: ").strip()

    area_id = api.get_area_id(city)
    if not area_id:
        print(f"Город {city} не найден. Попробуйте другой город.")
        return

    vacancies = api.get_vacancies(search_query=search_query, area=area_id)
    unique_companies = {}
    index = 1

    print("Список вакансий с уникальными компаниями:")
    for vacancy in vacancies.get('items', []):
        company_id = vacancy['employer']['id']
        if company_id not in unique_companies and index <= 20:
            print(f"{index}. Вакансия: {vacancy['name']}. Работодатель: \033[1m{vacancy['employer']['name']}\033[0m")
            unique_companies[index] = {'id': company_id, 'name': vacancy['employer']['name']}
            index += 1

    while True:
        selected_indexes = input(
            "Выберите номера до 10 компаний через пробел, "
            "от которых вы хотели бы получать данные о вакансиях (от 1 до 10): ").split()
        if not (1 <= len(selected_indexes) <= 10):
            print("Необходимо выбрать от 1 до 10 компаний. Попробуйте снова.")
            continue

        try:
            selected_indexes = [int(i) for i in selected_indexes]
        except ValueError:
            print("Пожалуйста, используйте только цифры для номеров вакансий.")
            continue

        if not all(1 <= i <= len(unique_companies) for i in selected_indexes):
            print("Некоторые из выбранных номеров вне диапазона доступных вакансий. Пожалуйста, проверьте ваш выбор.")
            continue

        break

    selected_companies = {unique_companies[i]['id']: unique_companies[i]['name'] for i in selected_indexes}

    # Проверяем наличие папки 'data' и создаём её, если отсутствует
    if not os.path.exists('data'):
        os.makedirs('data')

    with open('data/employers.json', 'w', encoding='utf-8') as f:
        json.dump(selected_companies, f, ensure_ascii=False, indent=4)

    print("Информация о выбранных компаниях сохранена.")


def create_database(database_name: str) -> None:
    """
    Создает базу данных PostgreSQL и таблицы в ней, если база данных с таким именем еще не существует.

    Args:
        database_name: Имя создаваемой базы данных.
    """
    params = config()
    # Параметры для подключения к системной базе данных для проверки существования целевой базы данных
    system_db_params = params.copy()
    system_db_params['dbname'] = 'postgres'

    try:
        # Подключение к системной базе данных без использования транзакции
        conn = psycopg2.connect(**system_db_params)
        conn.autocommit = True
        cur = conn.cursor()

        # Проверка существования базы данных
        cur.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (database_name,))
        exists = cur.fetchone()
        if not exists:
            # Создание базы данных, если она не существует
            cur.execute(f"CREATE DATABASE {database_name}")

        # Очистка ресурсов
        cur.close()
        conn.close()

        # Подключение к новосозданной базе данных
        params['dbname'] = database_name
        conn = psycopg2.connect(**params)
        conn.autocommit = True
        cur = conn.cursor()

        # Создание таблиц 'companies' и 'vacancies'
        cur.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                url TEXT
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS vacancies (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                area TEXT,
                salary_from INTEGER,
                salary_to INTEGER,
                currency TEXT,
                employer_id INTEGER REFERENCES companies(id),
                published_at TIMESTAMP,
                url TEXT NOT NULL,
                schedule TEXT,
                employment TEXT
            );
        """)
        print(f"База данных '{database_name}' и таблицы успешно созданы.")

        # Очистка ресурсов
        cur.close()
        conn.close()

    except psycopg2.Error as e:
        print(f"Произошла ошибка при создании базы данных: {e}")


def fill_database_with_companies_and_vacancies(database_name: str):
    """
    Заполняет базу данных информацией о компаниях и вакансиях из файла employers.json.

    Args:
        database_name: Имя базы данных для заполнения.
    """
    print(f"Заполнение базы данных '{database_name}' выбранными компаниями и их вакансиями...")
    db_manager = DBManager(database_name)  # Создаем экземпляр менеджера базы данных
    api = HeadHunterAPI()  # Создаем экземпляр API

    # Читаем файл employers.json
    with open('data/employers.json', 'r', encoding='utf-8') as file:
        companies = json.load(file)

    for company_id, company_name in companies.items():
        # Сохраняем информацию о компании в базе данных
        db_manager.insert_company(
            {'id': company_id, 'name': company_name, 'url': f"https://hh.ru/employer/{company_id}"})

        # Получаем вакансии для компании
        vacancies = api.get_company_vacancies(company_id)
        for vacancy in vacancies['items']:
            # Детальная информация о вакансии
            vacancy_details = api.get_vacancy_details(vacancy['id'])

            # Обработка даты и времени
            published_at_iso = vacancy_details['published_at']  # Получаем дату и время в ISO формате
            published_at = datetime.fromisoformat(published_at_iso)  # Преобразуем в datetime объект
            published_at_str = published_at.strftime('%Y-%m-%d')  # Преобразуем в нужный формат строки

            # Обработка зарплаты
            salary_info = vacancy_details.get('salary')
            if salary_info:
                salary_from = salary_info.get('from')
                salary_to = salary_info.get('to')
                currency = salary_info.get('currency')
            else:
                salary_from = None
                salary_to = None
                currency = None

            # Обработка остальных данных
            area = vacancy_details['area']['name']
            url = vacancy_details.get('alternate_url', '')
            schedule = vacancy_details.get('schedule', {}).get('name', '')
            employment = vacancy_details.get('employment', {}).get('name', '')

            # Сохранение информации о вакансии в базе данных
            db_manager.insert_vacancy({
                'id': vacancy_details['id'],
                'name': vacancy_details['name'],
                'area': area,
                'salary_from': salary_from,
                'salary_to': salary_to,
                'currency': currency,
                'employer_id': company_id,
                'published_at': published_at_str,
                'url': url,
                'schedule': schedule,
                'employment': employment
                # Добавьте остальные поля здесь
            })

    db_manager.close()
    print("База данных успешно заполнена выбранными компаниями и их вакансиями.")


def get_user_action():
    print("\nВыберите действие:")
    print("1 - Получить список всех компаний и количество вакансий у каждой компании")
    print("2 - Получить список всех вакансий")
    print("3 - Получить среднюю зарплату по вакансиям")
    print("4 - Получить список всех вакансий с зарплатой выше средней")
    print("5 - Найти вакансии по ключевому слову")
    print("6 - Выйти из программы")
    action = input("Ваш выбор: ")
    return action


def handle_action(action, db_manager):
    """
    Обрабатывает выбранное пользователем действие и выполняет соответствующие операции с базой данных.

    Args:
        action (str): Выбранное пользователем действие.
        db_manager (DBManager): Менеджер базы данных для выполнения операций.

    Returns:
        None
    """
    if action == "1":
        for company, count in db_manager.get_companies_and_vacancies_count():
            print(f"{company}: {count} вакансий")

    elif action == "2":
        vacancies = db_manager.get_all_vacancies()
        for i, vacancy in enumerate(vacancies, start=1):
            company_name, vacancy_name, salary_from, salary_to, url = vacancy
            salary_from = 'Не указано' if salary_from is None else str(salary_from)
            salary_to = 'Не указано' if salary_to is None else str(salary_to)
            print(
                f"{i}. Компания: {company_name}\n   Вакансия: {vacancy_name}\n"
                f"   Зарплата: от {salary_from} до {salary_to} руб.\n   (ссылка: {url})")
            print()

    elif action == "3":
        avg_salary = db_manager.get_avg_salary()
        avg_salary = 'Не указана' if avg_salary is None else f"{avg_salary:,.2f}"
        print(f"Средняя зарплата по всем вакансиям: {avg_salary} руб")

    elif action == "4":
        vacancies = db_manager.get_vacancies_with_higher_salary()
        for i, vacancy in enumerate(vacancies, start=1):
            name, salary_from, salary_to, url = vacancy
            salary_from = 'Не указано' if salary_from is None else str(salary_from)
            salary_to = 'Не указано' if salary_to is None else str(salary_to)
            print(
                f"{i}. Вакансия: {name}\n"
                f"   Зарплата: от {salary_from} до {salary_to} руб.\n   (ссылка: {url})")
            print()

    elif action == "5":
        keyword = input("Введите ключевое слово для поиска вакансий: ")
        vacancies = db_manager.get_vacancies_with_keyword(keyword)
        for i, vacancy in enumerate(vacancies, start=1):
            company_name, vacancy_name, salary_from, salary_to, url = vacancy
            salary_from = 'Не указано' if salary_from is None else str(salary_from)
            salary_to = 'Не указано' if salary_to is None else str(salary_to)
            print(
                f"{i}. Компания: {company_name}\n   Вакансия: {vacancy_name}\n"
                f"   Зарплата: от {salary_from} до {salary_to} руб.\n   (ссылка: {url})\n"
            )


def check_database_exists(db_name: str) -> bool:
    """
    Проверяет существование базы данных с заданным именем.

    Args:
        db_name (str): Имя базы данных для проверки.

    Returns:
        bool: True, если база данных существует, False в противном случае.
    """
    try:
        params = config()
        system_db_params = params.copy()
        system_db_params['dbname'] = 'postgres'

        # Подключение к системной базе данных без использования транзакции
        conn = psycopg2.connect(**system_db_params)
        conn.autocommit = True
        cur = conn.cursor()

        # Проверка существования базы данных
        cur.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (db_name,))
        exists = cur.fetchone()

        # Очистка ресурсов
        cur.close()
        conn.close()

        return bool(exists)
    except psycopg2.Error as e:
        print(f"Произошла ошибка при проверке существования базы данных: {e}")
        return False


if __name__ == "__main__":
    search_vacancies()
    get_user_action()
