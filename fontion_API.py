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

def get_data_debit(date_debut="2020-01-01", date_fin="2024-01-01", month=True, code_entite="U4300010", size=None):
    if size is None:
        size = 20000
    if month:
        grandeur_hydro = "QmM"
    else:
        grandeur_hydro = "QmnJ"
    url = f'https://hubeau.eaufrance.fr/api/v2/hydrometrie/obs_elab?code_entite={code_entite}&date_debut_obs_elab={date_debut}&date_fin_obs_elab={date_fin}&grandeur_hydro_elab={grandeur_hydro}&size={size}'
    data = get_data(url)
    return data