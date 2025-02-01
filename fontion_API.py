import requests

def get_data(url):
    headers = {
    'Accept': 'application/json'
    }
    response = requests.get(url, headers=headers)
    # Vérification si la requête a réussi
    return response.json()

def get_site_data():
    url = 'https://hubeau.eaufrance.fr/api/v2/hydrometrie/referentiel/sites?bbox=4.00&bbox=42.00&bbox=6.50&bbox=46.5&format=json&size=780' 
    return get_data(url)

