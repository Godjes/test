import requests
import xmlrpc.client
import base64
import time
import asyncio


start_time = time.time()

class Swapi:

    def __init__(self):
        self.base_url = "https://swapi.dev/api/"
        self.picture_url = 'https://starwars-visualguide.com/assets/img/characters/{}.jpg'
    
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
                planet_urls = [planet['homeworld'] for planet in data['results']]
                homeworld_data = {}
                for planet_url in planet_urls:
                    if planet_url not in homeworld_data:  # Check if we already have the data
                        homeworld_response = requests.get(planet_url)
                        if homeworld_response.status_code == 200:
                            homeworld = homeworld_response.json()
                            homeworld_data[planet_url] = homeworld
                        else:
                            print(f"Ошибка при выполнении запроса к {planet_url}: {homeworld_response.status_code}")

                for planet in data['results']:
                    homeworld_id = planet['homeworld'].split('/')[-2]
                    homeworld = homeworld_data[planet['homeworld']]
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

        self.common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(self.url))
        self.uid = self.common.authenticate(self.db, self.username, self.password, {})

        self.models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(self.url))

    def create_planet(self, create_planet_data: dict):
        return self.models.execute_kw(
            self.db, self.uid, self.password, 'res.planet', 'create',
            [create_planet_data]
        )

    def create_characters(self, character, image_data, new_planet_id):
        return self.models.execute_kw(
            self.db, self.uid, self.password, 'res.partner', 'create',
            [{'name': character['name'], 'image_1920': base64.b64encode(image_data).decode('utf-8'),
              'planet': new_planet_id}]
        )

    def get_character(self, character):
        return self.models.execute_kw(
                            self.db, self.uid, self.password, 'res.partner', 'search',
                            [[('name', '=', character['name'])]]
                        )

    def get_planet(self, name):
        return self.models.execute_kw(
            self.db, self.uid, self.password, 'res.planet', 'search',
            [[('name', '=', name)]]
        )

def main():
    swapi = Swapi()
    odoo_repo = Odoo()
    characters = swapi.get_characters()
    planets = swapi.get_planets()

    create_planet_data = []
    # Создание новых записей планет в базе данных Odoo
    for planet_id, planet_data in planets.items():

        existing_planet = odoo_repo.get_planet(planet_data['name'])

        if not existing_planet:
            diameter = int(planet_data['diameter']) if planet_data['diameter'] != "unknown" else 0
            population = int(planet_data['population']) if planet_data['population'] != "unknown" else 0
            rotation_period = int(planet_data['rotation_period']) if planet_data['rotation_period'] != "unknown" else 0
            orbital_period = int(planet_data['orbital_period']) if planet_data['orbital_period'] != "unknown" else 0

            new_planet_id = odoo_repo.create_planet(
                create_planet_data={
                    'name': planet_data['name'],
                    'diameter': str(diameter),
                    'population': str(population),
                    'rotation_period': str(rotation_period),
                    'orbital_period': str(orbital_period)
                }
            )
            create_planet_data.append(
                {
                    'name': planet_data['name'],
                    'diameter': str(diameter),
                    'population': str(population),
                    'rotation_period': str(rotation_period),
                    'orbital_period': str(orbital_period)
                }
            )

        else:
            new_planet_id = existing_planet[0]

        for character in characters:

            character_id = character['url'].split('/')[-2]
            character_planet_id = character['homeworld'].split('/')[-2]

            if character_planet_id == planet_id:

                existing_character = odoo_repo.get_character(character=character)

                if not existing_character:
                    image_data = swapi.download_images(character_id=character_id)

                    new_character_id = odoo_repo.create_characters(
                        character=character,
                        image_data=image_data,
                        new_planet_id=new_planet_id,
                    )
                else:
                    new_character_id = existing_character[0]
if __name__ == '__main__':
    main()
    print('готого мать твою')
    end_time = time.time()
    ends_time = end_time - start_time
    print(f'время выполнения {ends_time}')