import requests
import xmlrpc.client
import base64
import pprint

class Swapi:

    def __init__(self):
        self.base_url = "https://swapi.dev/api/"
    
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
                    homeworlds[planet['homeworld'].split('/')[-2]] = {
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
        base_url = 'https://starwars-visualguide.com/assets/img/characters/{}.jpg'.format(character_id)
        response = requests.get(base_url)
        if response.status_code == 200:
            return response.content
        else:
            print(f"Failed to download image for character {character_id}")
            return None
    


class Odoo:
    def __init__(self):
        # Подключение к серверу Odoo
        url = 'http://localhost:8069/'
        db = 'odoo16'
        username = 'admin'
        password = 'admin'

        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
        uid = common.authenticate(db, username, password, {})

        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

        swapi = Swapi()
        characters = swapi.get_characters()
        planets = swapi.get_planets()
        

        # Создание новых записей планет в базе данных Odoo
        for planet_id, planet_data in planets.items():
            existing_planet = models.execute_kw(
                db, uid, password, 'res.planet', 'search',
                [[('name', '=', planet_data['name'])]]
            )
            if not existing_planet:
                diameter = int(planet_data['diameter']) if planet_data['diameter'] != "unknown" else 0
                population = int(planet_data['population']) if planet_data['population'] != "unknown" else 0
                rotation_period = int(planet_data['rotation_period']) if planet_data['rotation_period'] != "unknown" else 0
                orbital_period = int(planet_data['orbital_period']) if planet_data['orbital_period'] != "unknown" else 0
                new_planet_id = models.execute_kw(
                    db, uid, password, 'res.planet', 'create',
                    [{'name': planet_data['name'],
                      'diameter': str(diameter),
                    'population': str(population),
                    'rotation_period': str(rotation_period),
                    'orbital_period': str(orbital_period)}]
        )
            else:
                new_planet_id = existing_planet[0]

            for character in characters:
                 if character['homeworld'].split('/')[-2] == planet_id:
                        existing_character = models.execute_kw(
                            db, uid, password, 'res.partner', 'search',
                            [[('name', '=', character['name'])]]
                        )
                        if not existing_character:
                            image_data = swapi.download_images(character['url'].split('/')[-2])
                            new_character_id = models.execute_kw(
                                db, uid, password, 'res.partner', 'create',
                                [{'name': character['name'], 'image_1920': base64.b64encode(image_data).decode('utf-8'),
                                  'planet': new_planet_id}]
                            )
                        else:
                            new_character_id = existing_character[0]

      
if __name__ == '__main__':
    Odoo()
    print('завершено')