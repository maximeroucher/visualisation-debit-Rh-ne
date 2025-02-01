# Gestion de la base de donnée du lac
from shapely.geometry import Point
from shapely import LineString
import geopandas as gpd
import pandas as pd

def find_nearest_segment(last_point, remaining_segments):
    min_dist = float('inf')
    nearest_segment = None
    nearest_index = None
    
    for i, seg in enumerate(remaining_segments):
        # Calculer les distances entre last_point et les deux extrémités du segment
        dist_to_last = last_point.distance(Point(seg.coords[0]))  # distance à first_point du segment
        dist_to_last2 = last_point.distance(Point(seg.coords[-1]))  # distance à end_point du segment
        
        # Trouver la distance la plus petite pour décider si on colle le segment avant ou après
        if dist_to_last < min_dist:
            min_dist = dist_to_last
            nearest_segment = seg
            nearest_index = i
            
        if dist_to_last2 < min_dist:
            min_dist = dist_to_last2
            nearest_segment = LineString(seg.coords[::-1])  # Inverser le segment
            nearest_index = i
    return nearest_segment, nearest_index

# Fonction pour ordonner les segments
def order_segments(segments, rhone, isrhone):
    ordered = []
    remaining_segments = segments[:]
    if isrhone:
        first_segment = segments[116] # Segment le plus proche du Rhône (à l'oeil)
    else:
        # Trouver le segment le plus proche du Rhône
        first_segment = None
        min_dist = float('inf')
        for seg in remaining_segments:
            if rhone.unary_union.distance(Point(seg.coords[0])) < min_dist:
                min_dist = rhone.unary_union.distance(Point(seg.coords[0]))
                first_segment = seg
            if rhone.unary_union.distance(Point(seg.coords[-1])) < min_dist:
                min_dist = rhone.unary_union.distance(Point(seg.coords[-1]))
                first_segment = LineString(seg.coords[::-1])  # Inverser le segment
    ordered.append(first_segment)
    while remaining_segments:
        last = ordered[-1]
        last_point = Point(last.coords[-1])  # Dernier point du segment actuel
        # Trouver le segment le plus proche
        nearest_segment, nearest_index = find_nearest_segment(last_point, remaining_segments)
        ordered.append(nearest_segment)  
        remaining_segments.pop(nearest_index)  # Retirer le segment utilisé
    return ordered

def linemerge(lines):
    merged = lines[0]
    for line in lines[1:]:
        merged = merged.union(line)
    return merged

# Fonction pour traiter chaque rivière
def process_river(group, rhone):
    isrhone = False
    if list(group["name"])[0] == "Le Rhône":
        isrhone = True
    segments = list(group["geometry"])
    # Ordonner les segments
    ordered_segments = order_segments(segments, rhone, isrhone)
    # Fusionner les segments ordonnés en une seule géométrie
    merged_line = linemerge(ordered_segments)
    return merged_line

# Appliquer la fonction à chaque rivière
def groupe_riviere(affluent_river):
    rhone = affluent_river[affluent_river["name"] == "Le Rhône"]
    affluent_river_groupe = (
        affluent_river.groupby("name")
        .apply(lambda group: process_river(group, rhone))
        .reset_index(name="geometry")
    )
    affluent_river_groupe = gpd.GeoDataFrame(affluent_river_groupe, crs=affluent_river.crs)
    return affluent_river_groupe

def create_points_along_line(line, distance):
    line_length = line.length
    points = []
    for d in range(0, int(line_length), distance):
        point = line.interpolate(d)
        points.append(point)
    return points

def create_point_distance(affluent_river_groupe, distance):
    distance = distance * 1000  # Convertir en mètres
    points_list, distance_list, riviere_list = [], [], []
    # Créer des points tous les 10 km le long de chaque rivière fusionnée
    for merged_line, name in zip(affluent_river_groupe["geometry"], affluent_river_groupe["name"]):
        points = create_points_along_line(merged_line, distance)
        points_list.extend(points)
        distance_list.extend(range(0, len(points)*distance, distance))
        riviere_list.extend([name]*len(points))
    distance_list = [distancei/1000 for distancei in distance_list]
    df_point = pd.DataFrame({'riviere': riviere_list, 'distance': distance_list})
    # Créer un GeoDataFrame pour les points
    points_distance = gpd.GeoDataFrame(df_point, geometry=points_list, crs=affluent_river_groupe.crs)
    return points_distance

# Trouver la rivière la plus proche de chaque point
def find_nearest_river(row, rivers_gdf):
    rivers_gdf = rivers_gdf.loc[rivers_gdf["name"] != row["riviere"]]  # Exclure la rivière actuelle
    nearest_river = rivers_gdf.loc[rivers_gdf.distance(row["geometry"]).idxmin()]
    return nearest_river['name']

def find_nearest_river_distance(row, rivers_gdf):
    rivers_gdf = rivers_gdf.loc[rivers_gdf["riviere"] != row["riviere"]]  # Exclure la rivière actuelle
    nearest_river = rivers_gdf.loc[rivers_gdf.distance(row["geometry"]).idxmin()]
    return nearest_river["distance"]

def find_site(affluent_river_groupe, point_site):
    # Effectuer la jointure spatiale avec une distance maximale de 1 km (1000 mètres)
    buffer = affluent_river_groupe.copy()
    buffer['geometry'] = buffer.geometry.buffer(1000)  # Créer un buffer de 1 km autour de chaque rivière
    # Jointure spatiale pour trouver les points dans le rayon de 1 km
    joined = gpd.sjoin(point_site, buffer, how='inner', predicate='within')
    # Ajouter une colonne 'name' avec le nom de la rivière
    joined['river_name'] = joined['name']
    return joined

def get_nearest_distance(row, points_distance):
    # Trouver le point le plus proche de chaque point dans 'joined' dans 'point_distance'
    points_distance = points_distance.loc[points_distance['riviere'] == row.river_name]
    nearest_point = points_distance.geometry.distance(row.geometry).idxmin()
    # Récupérer le point le plus proche
    distance = points_distance.loc[nearest_point, "distance"]
    return distance