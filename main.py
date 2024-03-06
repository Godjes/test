import base64
import logging
import sys
import xmlrpc.client
from http import HTTPStatus
from typing import Union

import requests

from exceptions import ExceptionStatusError
import time

t = time.time()

class Swapi:
    """
    Класс для получения данных.
    ...
    Атрибуты
    --------
    base_url : str
        адрес для запроса данных
    picture_url : str
        адрес для получения изображений
    Методы
    ------
    get_characters():
        Получает данные о всех персонажах.
    get_planets():
        Получает данные о всех планетах.
    get_planets():
        Получает данные о всех планетах.
    download_images():
        Получает изображения для всех персонажей.
    """

    def __init__(self) -> None:
        self.base_url: str = "https://swapi.dev/api/"
        self.picture_url: str = (
            'https://starwars-visualguide.com/assets/img/characters/{}.jpg'
        )

    def get_characters(self) -> list:
        """
        Получает всю информацию о персонажах.
        ---------
        Возвращаемое значение
        ---------------------
        list
        """
        url: str = f"{self.base_url}people/"
        characters: list = []

        while url:
            try:
                logging.info(f'Request running {url}')
                response = requests.get(url)
            except requests.RequestException as error:
                raise ConnectionError(f'Request failed {url}, {error}')
            if response.status_code != HTTPStatus.OK:
                raise ExceptionStatusError((
                    f"Program failure: {url} "
                    f"{response.status_code}"
                    f"{response.reason}"
                    f"{response.text}"
                    )
                )
            data: dict = response.json()
            characters.extend(data['results'])
            url = data['next']
        return characters

    def get_planets(self) -> dict:
        """
        Получает всю информацию о планетах.
        ---------
        Возвращаемое значение
        ---------------------
        dict
        """
        url: str = f"{self.base_url}people/"
        homeworlds: dict = {}
        homeworld_urls = set()

        while url:
            try:
                logging.info(f'Выполняется запрос {url}')
                response = requests.get(url)
            except requests.RequestException as error:
                raise ConnectionError(f'Сбой программы {url}, {error}')

            if response.status_code != HTTPStatus.OK:
                raise ExceptionStatusError((
                    f"Сбой программы: {url} "
                    f"{response.status_code}"
                    f"{response.reason}"
                    f"{response.text}"
                    )
                )
            data: dict = response.json()
            for planet in data['results']:
                homeworld_urls.add(planet['homeworld'])

            url = data['next']
        for homeworld_url in homeworld_urls:
            try:
                logging.info(f'Выполняется запрос {homeworld_url}')
                homeworld_response = requests.get(homeworld_url)
                homeworld_data = homeworld_response.json()  
                homeworld_id = homeworld_url.split('/')[-2]
                homeworlds[homeworld_id] = {
                    'name': homeworld_data['name'],
                    'diameter': homeworld_data['diameter'],
                    'population': homeworld_data['population'],
                    'rotation_period': homeworld_data['rotation_period'],
                    'orbital_period': homeworld_data['orbital_period'],
                }
            except requests.RequestException as error:
                raise ConnectionError(f'Сбой программы {homeworld_url}, {error}')

            if homeworld_response.status_code != HTTPStatus.OK:
                raise ExceptionStatusError((
                    f"Сбой программы: {homeworld_url} "
                    f"{homeworld_response.status_code}"
                    f"{homeworld_response.reason}"
                    f"{homeworld_response.text}"
                    )
                )

        return homeworlds

    def download_images(self, character_id: int) -> Union[bytes, None]:
        """
        Получает изображение персонажей.
        ---------
        Возвращаемое значение
        ---------------------
        bytes
        """
        try:
            logging.info((
                f'Request running '
                f'{self.picture_url.format(character_id)}'
                )
            )
            response = requests.get(self.picture_url.format(character_id))
        except requests.RequestException as error:
            raise ConnectionError((
                f'Program failure '
                f'{self.picture_url.format(character_id)}, {error}'))
        if response.status_code != HTTPStatus.OK:
            logging.error(
                f'Не удалось получить изображения '
                f'для {character_id}'
            )
            return None
        return response.content


class Odoo:
    """
    Класс для получения данных.
    ...
    Атрибуты
    --------
    url : str
        адрес сервера
    db : str
        название БД
    username : str
        логин superuser
    password : str
        пароль superuser
    Методы
    ------
    create_planet():
        создает планету в БД
    create_characters():
        создает контакт в БД.
    get_character():
        Получает данные о контакте в Odoo.
    get_planet():
        Получает данные о планете в Odoo
    """

    def __init__(self):
        self.url = 'http://localhost:8069/'
        self.db = 'odoo16'
        self.username = 'admin'
        self.password = 'admin'

        self.common = xmlrpc.client.ServerProxy(
            '{}/xmlrpc/2/common'.format(self.url)
        )
        self.uid = self.common.authenticate(
            self.db, self.username, self.password, {}
        )

        self.models = xmlrpc.client.ServerProxy(
            '{}/xmlrpc/2/object'.format(self.url)
        )

    def create_planet(self, create_planet_data):
        """
        создает новую запись в БД
        ---------
        create_planet_data : dict
            словарь с данными о планете
        ---------------------
        """
        return self.models.execute_kw(
            self.db, self.uid, self.password, 'res.planet', 'create',
            [create_planet_data]
        )

    def create_characters(
            self, character: dict, image_data: bytes, new_planet_id: int
    ):
        """
        создает новую запись в БД
        ---------
        character : dict
            данные о персонаже
        image_data : bytes
            изображение персонажа
        new_planet_id: int
            id планеты из БД
        ---------------------
        """
        try:
            if image_data is not None:
                encoded_image = base64.b64encode(image_data).decode('utf-8')
                return self.models.execute_kw(
                    self.db, self.uid, self.password, 'res.partner', 'create',
                    [{'name': character['name'],
                        'image_1920': encoded_image,
                        'planet': new_planet_id}]
                    )
            else:
                return self.models.execute_kw(
                    self.db, self.uid, self.password, 'res.partner', 'create',
                    [{'name': character['name'],
                        'planet': new_planet_id}]
                    )
        except Exception as e:
            log_message = (f"Failed to create:"
                           f"Entity: Character,"
                           f"Name: {character['name']}, Error: {e}"
                           )
            logging.error(log_message)

    def get_character(self, character):
        """
        Получает данные о контакте в Odoo.
        ---------
        character : dict
            данные о персонаже
        ---------------------
        """
        return self.models.execute_kw(
                            self.db, self.uid, self.password, 'res.partner',
                            'search',
                            [[('name', '=', character['name'])]]
                        )

    def get_planet(self, name):
        """
        Получает данные о планете в Odoo
        ---------
        name : dict
            данные о персонаже
        ---------------------
        """
        return self.models.execute_kw(
            self.db, self.uid, self.password, 'res.planet', 'search',
            [[('name', '=', name)]]
        )


class DataProcessor:
    """
    Класс инициализрующий наполнение БД.
    ...
    Атрибуты
    --------
    swapi : class
        Экземпляр класса Swapi
    odoo_repo : class
        Экземпляр класса Odoo
    ------
    process_data():
        заполнение БД требуемыми данными
    """
    def __init__(self, swapi, odoo_repo):
        self.swapi = swapi
        self.odoo_repo = odoo_repo

    def process_data(self):
        """
        заполнение БД требуемыми данными
        """
        characters = self.swapi.get_characters()
        planets = self.swapi.get_planets()

        for planet_id, planet_data in planets.items():
            try:
                existing_planet = self.odoo_repo.get_planet(
                    planet_data['name']
                )
                if not existing_planet:
                    diameter = planet_data['diameter'] if planet_data['diameter'] != "unknown" else 0
                    population = planet_data['population'] if planet_data['population'] != "unknown" else 0
                    rotation_period = planet_data['rotation_period'] if planet_data['rotation_period'] != "unknown" else 0
                    orbital_period = planet_data['orbital_period'] if planet_data['orbital_period'] != "unknown" else 0

                    new_planet_id = self.odoo_repo.create_planet(
                        create_planet_data={
                            'name': planet_data['name'],
                            'diameter': str(diameter),
                            'population': str(population),
                            'rotation_period': str(rotation_period),
                            'orbital_period': str(orbital_period)
                        }
                    )
                    log_message = (f"Entity: Planet, "
                                   f"Name: {planet_data['name'],}, "
                                   f"Remote ID: {planet_id}, "
                                   f"Odoo ID: {new_planet_id}"
                                   )
                    logging.info(log_message)
                else:
                    new_planet_id = existing_planet[0]
                    logging.info(f"Planet already exist {planet_data['name']}")
            except Exception as e:
                logging.error(f'Failed to create: {log_message}, {e}')
            for character in characters:

                character_id = character['url'].split('/')[-2]
                character_planet_id = character['homeworld'].split('/')[-2]

                if character_planet_id == planet_id:
                    try:
                        existing_character = self.odoo_repo.get_character(character=character)

                        if not existing_character:
                            image_data = self.swapi.download_images(character_id=character_id)

                            new_character_id = self.odoo_repo.create_characters(
                                character=character,
                                image_data=image_data,
                                new_planet_id=new_planet_id,
                            )
                            log_message = (f"Entity: Character, "
                                           f"Name: {character['name']}, "
                                           f"Remote ID: {character_id}, "
                                           f"Odoo ID: {new_character_id}")
                            logging.info(log_message)
                        else:
                            new_character_id = existing_character[0]
                            logging.info(
                                f"Contact already exist {character['name']}"
                            )
                    except Exception as e:
                        log_message = (
                            f"не удалось создать: "
                            f"Entity: Character, "
                            f"Name: {character['name']}, "
                            f"Remote ID: {character_id}, "
                            f"Odoo ID: {new_character_id}")
                        logging.error(log_message, e)


def main():
    swapi = Swapi()
    odoo_repo = Odoo()
    processor = DataProcessor(swapi, odoo_repo)
    processor.process_data()


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format=(
            '[%(asctime)s] [%(levelname)s] [%(funcName)s] [%(lineno)d]'
            '> %(message)s'
        ),
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(__file__ + '.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    main()