import requests


class HeadHunterAPI:
    """Класс для взаимодействия с публичным API hh.ru."""

    def __init__(self):
        """Инициализирует базовый URL для API hh.ru."""
        self.base_url = 'https://api.hh.ru'

    def get_vacancies(self, search_query: str, area: str = None, page: int = 0) -> dict:
        """
        Получает вакансии по заданным параметрам.

        Args:
            search_query: Поисковый запрос для вакансий.
            area: Идентификатор региона (необязательно).
            page: Номер страницы результатов поиска.

        Returns:
            Словарь с данными о вакансиях.
        """
        params = {
            'text': search_query,
            'area': area,
            'page': page,
            'per_page': 50  # Количество результатов на странице
        }
        response = requests.get(f"{self.base_url}/vacancies", params=params)
        response.raise_for_status()  # Если запрос не успешен, вызывается исключение
        return response.json()

    def get_area_id(self, city_name: str, areas=None) -> str:
        """
        Рекурсивно ищет ID региона по его названию во всех уровнях иерархии регионов.

        Args:
            city_name (str): Название города для поиска.
            areas (list, optional): Список регионов для поиска. По умолчанию None, что означает загрузку всех регионов.

        Returns:
            str: ID региона, если найден, иначе пустая строка.
        """
        if areas is None:
            response = requests.get(f"{self.base_url}/areas")
            response.raise_for_status()
            areas = response.json()

        for area in areas:
            if city_name.lower() in area['name'].lower():
                return area['id']
            if 'areas' in area and area['areas']:
                sub_area_id = self.get_area_id(city_name, area['areas'])
                if sub_area_id:
                    return sub_area_id

        return ""  # Если ничего не найдено

    def get_vacancy_details(self, vacancy_id: str) -> dict:
        """
        Получает детальную информацию о вакансии по её ID.
        """
        try:
            response = requests.get(f"{self.base_url}/vacancies/{vacancy_id}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"Произошла ошибка при получении информации о вакансии {vacancy_id}: {e}")
            return {}  # Возвращаем пустой словарь в случае ошибки

    def get_company_vacancies(self, company_id: str, page: int = 0) -> dict:
        """
        Получает список вакансий для заданной компании по её ID.
        """
        params = {'employer_id': company_id, 'page': page, 'per_page': 20}
        response = requests.get(f"{self.base_url}/vacancies", params=params)
        response.raise_for_status()
        return response.json()

