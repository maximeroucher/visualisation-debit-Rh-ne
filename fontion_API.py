import requests
import pandas as pd

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

def get_data_debit(date_debut="2020-01-01", date_fin="2024-01-01", month=True, code_entite="", size=None):
    # exemple code_entite = "U4300010"
    if size is None:
        size = 20000
    if month:
        grandeur_hydro = "QmM"
    else:
        grandeur_hydro = "QmnJ"
    url = f'https://hubeau.eaufrance.fr/api/v2/hydrometrie/obs_elab?code_entite={code_entite}&date_debut_obs_elab={date_debut}&date_fin_obs_elab={date_fin}&grandeur_hydro_elab={grandeur_hydro}&size={size}'
    data = get_data(url)
    list_data = data["data"]
    while data["next"] is not None:
        url = data["next"]
        data = get_data(url)
        list_data += data["data"]
    return list_data

def build_graph(confluence, uniquemerged_array):
    def group_points_by_river(uniquemerged_array):
        grouped_points = {}
        # iterate on dataframe
        for index, row in uniquemerged_array.iterrows():
            river_name = row["river_name"]
            if river_name not in grouped_points:
                grouped_points[river_name] = []
            grouped_points[river_name].append(row)
        return grouped_points
    grouped_points = group_points_by_river(uniquemerged_array)
    graph = []
    for river, points in grouped_points.items():
        rhone_distance = next((r["distance_rhone"] for id, r in confluence.iterrows() if r["riviere"] == river), None)
        sort_points = sorted(points, key=lambda x: x["distance"], reverse=True)
        # Ajouter les liens entre les points de la rivière
        for i in range(len(sort_points) - 1):
            graph.append({
                "source": f"{sort_points[i]['river_name']}_{sort_points[i]['distance']}",
                "target": f"{sort_points[i + 1]['river_name']}_{sort_points[i + 1]['distance']}",
                "value": sort_points[i]['resultat_obs_elab'],
                "distance_end": sort_points[i]['distance'] + rhone_distance if river != "Le Rhône" else sort_points[i]['distance'],
                "code_site": sort_points[i]['code_site']
            })
        
        # Gérer le dernier point
        last_point = sort_points[-1]
        if river == "Le Rhône":
            graph.append({
                "source": f"{last_point['river_name']}_{last_point['distance']}",
                "target": "La mer Méditerranée",
                "value": last_point['resultat_obs_elab'],
                "distance_end": last_point['distance'],
                "code_site": last_point['code_site']
            })
            continue  # Aucun lien supplémentaire pour Le Rhône
        
        if rhone_distance is None:
            continue
        
        closest_point = next((p for id, p in uniquemerged_array.iterrows()
                              if p["river_name"] == "Le Rhône" and p["distance"] < rhone_distance), None)
        if closest_point is not None:
            graph.append({
                "source": f"{last_point['river_name']}_{last_point['distance']}",
                "target": f"{closest_point['river_name']}_{closest_point['distance']}",
                "value": last_point['resultat_obs_elab'],
                "distance_end": last_point['distance'] + rhone_distance,
                "code_site": last_point['code_site']
            })
    graph = pd.DataFrame(graph)
    # si un point à la meme source et target on l'enleve
    graph = graph.loc[graph["source"] != graph["target"]]
    return graph

def create_graph(site_affluent_rhone, confluence, date="2024-01-01", month=False):
    data = pd.DataFrame(get_data_debit(date_debut=date, date_fin=date, month=month, code_entite=""))
    data = pd.merge(data, site_affluent_rhone, on="code_site", how="inner", suffixes=("", "_y"))
    data = data.drop_duplicates(subset="code_site", keep="first")
    graph = build_graph(confluence, data)
    return graph

def create_graph_periode(site_affluent_rhone, confluence, date_debut, date_fin, month=True):
    date_debut = pd.to_datetime(date_debut, format='%Y-%m-%d')
    date_fin = pd.to_datetime(date_fin, format='%Y-%m-%d')
    liste_graph = []
    # iterer sur les jours si month = False sinon sur les mois en faisant des couples debut du mois et fin du mois en commencant par le debut du mois de date_debut et en finissant par la fin du mois de date_fin
    if month:
        liste_date = pd.date_range(start=date_debut, end=date_fin, freq='MS')
    else:
        liste_date = pd.date_range(start=date_debut, end=date_fin, freq='D')
    for date in liste_date:
        graph = create_graph(site_affluent_rhone, confluence, date, month)
        graph["date"] = date
        liste_graph.append(graph)
    graph = pd.concat(liste_graph)
    return graph