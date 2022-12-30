import pandas as pd
import numpy as np
import geopandas as gpd
import os
from geopy.distance import geodesic
from shapely.geometry import Point

from typing import List, Tuple

FREQ = 15
lane_type = {(3, 4, 5, 6, 7, 8, 17, 18, 19): 'right',
             (12, 13, 14, 15, 16, 26, 27, 28): 'up',
             (0, 1, 2, 20, 21, 22, 23, 24, 25): 'left',
             (29, 30, 31, 32, 33, 34, 9, 10, 11): 'down'}

in_type = set([3, 4, 5, 6, 7, 8, 12, 13, 14, 15, 16, 20, 21, 22, 23, 24, 25, 29, 30, 31, 32, 33, 34])

lane_dict = {lane: t for lanes, t in lane_type.items() for lane in lanes}
in_dict = {lane: 'in' if lane in in_type else 'out' for lane in range(35)}

def extract_bbox(group, traffic_light='green'):
    if traffic_light == 'green':
        return {index: np.array([list(row[[f'boundingBox{i}X', f'boundingBox{i}Y']]) for i in range(1, 5)]) for index, row in group.iterrows()}
    else:
        return None

def sort_bbox(bbox_list, direction):
    if direction == 'right':
        return sorted(bbox_list.items(), key=lambda x: x[1][:, 0].max(), reverse=False)
    elif direction == 'up':
        return sorted(bbox_list.items(), key=lambda x: x[1][:, 1].max(), reverse=True)
    elif direction == 'left':
        return sorted(bbox_list.items(), key=lambda x: x[1][:, 0].max(), reverse=True)
    elif direction == 'down':
        return sorted(bbox_list.items(), key=lambda x: x[1][:, 1].max(), reverse=False)
    else:
        return None

def get_dist(bbox_1: np.ndarray, 
             bbox_2: np.ndarray, 
             bbox_latlon_1: np.ndarray,
             bbox_latlon_2: np.ndarray,
             direction: str) -> float:
    if direction == 'right':
        return get_latlon_dist(bbox_latlon_2[bbox_2[:, 0].argsort()[:2]].mean(axis=0), bbox_latlon_1[bbox_1[:, 0].argsort()[-2:]].mean(axis=0))
    elif direction == 'up':
        return get_latlon_dist(bbox_latlon_2[bbox_2[:, 1].argsort()[-2:]].mean(axis=0), bbox_latlon_1[bbox_1[:, 1].argsort()[:2]].mean(axis=0))
    elif direction == 'left':
        return get_latlon_dist(bbox_latlon_1[bbox_1[:, 0].argsort()[:2]].mean(axis=0), bbox_latlon_2[bbox_2[:, 0].argsort()[-2:]].mean(axis=0))
    elif direction == 'down':
        return get_latlon_dist(bbox_latlon_1[bbox_1[:, 1].argsort()[-2:]].mean(axis=0), bbox_latlon_2[bbox_2[:, 1].argsort()[:2]].mean(axis=0))
    else:
        return None

def get_latlon_dist(pt1, pt2):
    return 1e3 * geodesic(pt1, pt2).km

def get_latlon_bbox(index_list: List[int], group: pd.DataFrame, traffic_light: str='green') -> List[Tuple[float, float]]:
    if traffic_light == 'green':
        return {index: np.array([list(row[[f'boundingBox{i}Lon', f'boundingBox{i}Lat']]) for i in range(1, 5)]) for index, row in group.iterrows()}
    else:
        return None

def extract_info(data: pd.DataFrame):
    """
    Extracts the information from the csv file
    """
    relative_speed_list = []
    speed_list = []
    distance_list = []
    for cnt, (index, group) in enumerate(data.groupby(['frameNum', 'laneId'])):
        frame_num, lane_id = index
        if lane_id >= 35:
            continue
        else:
            bbox_list = extract_bbox(group)
            direction = lane_dict[lane_id]
            bbox_list = sort_bbox(bbox_list, direction)
            latlon_bbox_list = get_latlon_bbox([item[0] for item in bbox_list], group)
            for i in range(len(bbox_list) - 1):
                idx_1, idx_2 = bbox_list[i][0], bbox_list[i + 1][0]
                relative_speed = group.loc[idx_1, 'speed'] - group.loc[idx_2, 'speed']
                speed = group.loc[idx_1, 'speed']
                distance = get_dist(bbox_list[i][1], 
                                    bbox_list[i + 1][1],
                                    latlon_bbox_list[idx_1],
                                    latlon_bbox_list[idx_2], 
                                    direction)
                            
                data.loc[idx_1, 'relative_speed'] = relative_speed
                data.loc[idx_1, 'speed'] = speed
                data.loc[idx_1, 'distance'] = distance                  
                
                # relative_speed_list.append(relative_speed)
                # speed_list.append(speed)
                # distance_list.append(distance)
        print(cnt, end='\r')
    # return relative_speed_list, speed_list, distance_list
    return data

if __name__ == '__main__':
    data = pd.DataFrame()
    for file in os.listdir('Alafaya'):
        if file.endswith('.csv'):
            data = data.append(pd.read_csv('Alafaya/University@Alafaya-01.csv'))
    data = data[data['frameNum'].apply(lambda x: x % FREQ == 0)]
    # pts = gpd.GeoDataFrame(geometry=data[['carCenterLon', 'carCenterLat']].apply(lambda x: Point(x), axis=1)).set_crs({'init': 'epsg:4326'}).to_crs({'init': 'epsg:3857'})
    # data[['x', 'y']] = pts.apply(lambda x: [x.geometry.x, x.geometry.y], axis=1)
    data = extract_info(data)
    # results = pd.DataFrame({'relative_speed': relative_speed_list, 'speed': speed_list, 'distance': distance_list})
    data.to_csv('results.csv', index=False)