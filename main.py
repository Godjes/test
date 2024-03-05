import base64
import time
import xmlrpc.client
import logging
import requests
import sys

start_time = time.time()


class Swapi:

    def __init__(self):
        self.base_url = "https://swapi.dev/api/"
        self.picture_url = (
            'https://starwars-visualguide.com/assets/img/characters/{}.jpg'
        )

    def get_characters(self):
        url = f"{self.base_url}people/"
        characters = []

        while url:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                characters.extend(data['results'])
                url = data['next']
            else:
                print("Failed to retrieve data from SWAPI")
                break

        return characters

    def get_planets(self):
        url = f"{self.base_url}people/"
        homeworlds = {}
        while url:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                for planet in data['results']:
                    homeworld = requests.get(planet['homeworld'])
                    homeworld = homeworld.json()
                    homeworld_id = planet['homeworld'].split('/')[-2]
                    homeworlds[homeworld_id] = {
                        'name': homeworld['name'],
                        'diameter': homeworld['diameter'],
                        'population': homeworld['population'],
                        'rotation_period': homeworld['rotation_period'],
                        'orbital_period': homeworld['orbital_period'],
                    }
                url = data['next']
            else:
                print("Ошибка при выполнении запроса:", response.status_code)

        return homeworlds

    def download_images(self, character_id):
        response = requests.get(self.picture_url.format(character_id))
        if response.status_code == 200:
            return response.content
        else:
            print(f"Failed to download image for character {character_id}")
            return None


class Odoo:
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
        return self.models.execute_kw(
            self.db, self.uid, self.password, 'res.planet', 'create',
            [create_planet_data]
        )

    def create_characters(self, character, image_data, new_planet_id):
        try:
            if image_data is not None:
                encoded_image = base64.b64encode(image_data).decode('utf-8')
            else:
                encoded_image = None

            return self.models.execute_kw(
                self.db, self.uid, self.password, 'res.partner', 'create',
                [{'name': character['name'],
                  'image_1920': encoded_image,
                  'planet': new_planet_id}]
            )
        except Exception as e:
            log_message = (f"Failed to create:"
                           f"Entity: Character,"
                           f"Name: {character['name']}, Error: {e}"
                           )
            logging.error(log_message)

    def get_character(self, character):
        return self.models.execute_kw(
                            self.db, self.uid, self.password, 'res.partner',
                            'search',
                            [[('name', '=', character['name'])]]
                        )

    def get_planet(self, name):
        return self.models.execute_kw(
            self.db, self.uid, self.password, 'res.planet', 'search',
            [[('name', '=', name)]]
        )


class DataProcessor:
    def __init__(self, swapi, odoo_repo):
        self.swapi = swapi
        self.odoo_repo = odoo_repo

    def process_data(self):
        characters = self.swapi.get_characters()
        planets = self.swapi.get_planets()

        # Создание новых записей планет в базе данных Odoo
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
                    log_message = (f"Entity: Planet,"
                                   f"Name: {planet_data['name'],},"
                                   f"Remote ID: {planet_id},"
                                   f"Odoo ID: {new_planet_id}"
                                   )
                    logging.info(log_message)
                else:
                    new_planet_id = existing_planet[0]
            except Exception as e:
                logging.error(f'Не удалось создать: {log_message}, {e}')
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
                            log_message = f"Entity: Character, Name: {character['name']}, Remote ID: {character_id}, Odoo ID: {new_character_id}"
                            logging.info(log_message)
                        else:
                            new_character_id = existing_character[0]
                    except Exception as e:
                        log_message = f"не удалось создать: Entity: Character, Name: {character['name']}, Remote ID: {character_id}, Odoo ID: {new_character_id}"
                        logging.error(log_message, e)


def main():
    swapi = Swapi()
    odoo_repo = Odoo()
    processor = DataProcessor(swapi, odoo_repo)
    processor.process_data()


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
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
