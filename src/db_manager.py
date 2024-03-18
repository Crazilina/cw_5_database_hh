import psycopg2
from .config import config


class DBManager:
    """
    Класс для управления базой данных, включая операции вставки и выборки данных.
    """

    def __init__(self, database_name=None):
        params = config()
        if database_name:
            params['dbname'] = database_name
        self.conn = psycopg2.connect(**params)

    def insert_company(self, company: dict) -> None:
        """
        Вставляет информацию о компании в таблицу companies.
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO companies (id, name, url) VALUES (%s, %s, %s)
                    ON CONFLICT (id) DO NOTHING;
                """, (company['id'], company['name'], company['url']))
                self.conn.commit()
        except psycopg2.Error as e:
            print(f"Произошла ошибка при вставке компании: {e}")
            self.conn.rollback()

    def insert_vacancy(self, vacancy: dict) -> None:
        """
        Вставляет информацию о вакансии в таблицу vacancies.
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO vacancies (id, name, area, salary_from, salary_to, currency, employer_id, 
                    published_at, url, schedule, employment)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING;
                """, (vacancy['id'], vacancy['name'], vacancy['area'], vacancy['salary_from'], vacancy['salary_to'],
                      vacancy['currency'], vacancy['employer_id'], vacancy['published_at'], vacancy['url'],
                      vacancy.get('schedule'), vacancy.get('employment')))
                self.conn.commit()
        except psycopg2.Error as e:
            print(f"Произошла ошибка при вставке вакансии: {e}")
            self.conn.rollback()

    def get_companies_and_vacancies_count(self):
        """Получает список всех компаний и количество вакансий у каждой компании."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT companies.name, COUNT(vacancies.id) AS vacancies_count
                    FROM companies
                    JOIN vacancies ON companies.id = vacancies.employer_id
                    GROUP BY companies.name
                    ORDER BY vacancies_count DESC;
                """)
                return cur.fetchall()
        except psycopg2.Error as e:
            print(f"Произошла ошибка при получении списка компаний и количества вакансий: {e}")
            return []

    def get_all_vacancies(self):
        """Получает список всех вакансий с указанием названия компании,
        названия вакансии, зарплаты и ссылки на вакансию."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT companies.name, vacancies.name, vacancies.salary_from, vacancies.salary_to, vacancies.url
                    FROM vacancies
                    JOIN companies ON vacancies.employer_id = companies.id;
                """)
                vacancies = cur.fetchall()

                formatted_vacancies = []
                for vacancy in vacancies:
                    company_name, vacancy_name, salary_from, salary_to, url = vacancy
                    salary_from = 'Не указано' if salary_from is None else f"{salary_from:,.2f}"
                    salary_to = 'Не указано' if salary_to is None else f"{salary_to:,.2f}"
                    formatted_vacancies.append((company_name, vacancy_name, salary_from, salary_to, url))

                return formatted_vacancies
        except psycopg2.Error as e:
            print(f"Произошла ошибка при получении списка всех вакансий: {e}")
            return []

    def get_avg_salary(self):
        """Получает среднюю зарплату по вакансиям."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT AVG((salary_from + salary_to) / 2)
                    FROM vacancies
                    WHERE salary_from IS NOT NULL AND salary_to IS NOT NULL;
                """)
                avg_salary = cur.fetchone()[0]
                return avg_salary
        except psycopg2.Error as e:
            print(f"Произошла ошибка при получении средней зарплаты по вакансиям {e}")
            return []

    def get_vacancies_with_higher_salary(self):
        """Получает список всех вакансий, у которых минимальная зарплата выше средней по всем вакансиям."""
        avg_salary = self.get_avg_salary()
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT name, salary_from, salary_to, url
                    FROM vacancies
                    WHERE salary_from > %s;
                """, (avg_salary,))
                vacancies = cur.fetchall()

                formatted_vacancies = []
                for vacancy in vacancies:
                    name, salary_from, salary_to, url = vacancy
                    salary_from = 'Не указано' if salary_from is None else salary_from
                    salary_to = 'Не указано' if salary_to is None else salary_to
                    formatted_vacancies.append((name, salary_from, salary_to, url))

                return formatted_vacancies
        except psycopg2.Error as e:
            print(f"Произошла ошибка при получении списка всех вакансий, "
                  f"у которых минимальная зарплата выше средней по всем вакансиям {e}")
            return []

    def get_vacancies_with_keyword(self, keyword: str):
        """Получает список всех вакансий, в названии которых содержатся переданные в метод слова."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT companies.name, vacancies.name, vacancies.salary_from, vacancies.salary_to, vacancies.url
                    FROM vacancies
                    JOIN companies ON vacancies.employer_id = companies.id
                    WHERE vacancies.name ILIKE %s;
                """, (f"%{keyword}%",))
                vacancies = cur.fetchall()

                formatted_vacancies = []
                for vacancy in vacancies:
                    company_name, vacancy_name, salary_from, salary_to, url = vacancy
                    salary_from = 'Не указано' if salary_from is None else salary_from
                    salary_to = 'Не указано' if salary_to is None else salary_to
                    formatted_vacancies.append((company_name, vacancy_name, salary_from, salary_to, url))

                return formatted_vacancies
        except psycopg2.Error as e:
            print(f"Произошла ошибка при получении списка всех вакансий,"
                  f" в названии которых содержатся переданные в метод слова {e}")
            return []

    def close(self) -> None:
        """
        Закрывает соединение с базой данных.
        """
        self.conn.close()
