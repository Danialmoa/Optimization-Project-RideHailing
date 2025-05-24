import h3
import pandas as pd
import random
import numpy as np
from geopy.distance import geodesic


class MapData:
    def __init__(self):
        self.h3_resolution = 7
        self.h3_index_to_district = {}
        
        self.districts = self.load_data()
        for district in self.districts:
            self.h3_index_to_district[district] = district
            
        self.distance_matrix = np.zeros((len(self.districts), len(self.districts)))
        
        for i in range(len(self.districts)):
            for j in range(len(self.districts)):
                if i == j:
                    self.distance_matrix[i, j] = 0
                else:
                    self.distance_matrix[i, j] = self._air_distance(self.districts[i], self.districts[j])

        self.hexagon_weights = self._calculate_demand_weights()
        
    def load_data(self):
        # https://www.kaggle.com/datasets/asjad99/rome-taxi-data-subset
        driver_data = pd.read_csv('data/databases/taxi_data_subset.csv')
        longitude = driver_data['Longitude']
        latitude = driver_data['Latitude']
        self.points = list(zip(latitude, longitude))
        self.h3_indices = [self._get_h3_index(lng, lat) for lat, lng in self.points]
        self.h3_indices = [self._expand_one_k_ring(h3_index) for h3_index in self.h3_indices]
        return np.unique(self.h3_indices)

    def _get_h3_index(self, lat, lng):
        return h3.latlng_to_cell(lat, lng, self.h3_resolution)
    
    def _get_location_center(self, h3_index):
        """Get center coordinates of an H3 index"""
        return h3.cell_to_latlng(h3_index)
    
    def _expand_one_k_ring(self, h3_index):
        return h3.grid_disk(h3_index, 1)

    def _air_distance(self, h3_index_1, h3_index_2):
        h3_index_1_center = self._get_location_center(h3_index_1)
        h3_index_2_center = self._get_location_center(h3_index_2)
        return geodesic(h3_index_1_center, h3_index_2_center).kilometers
        
    def _calculate_demand_weights(self):
        important_centers = [
            (41.9028, 12.4964),  # Historic Center (Pantheon)
            (41.9011, 12.5024),  # Termini Station
            (41.7999, 12.2462),  # Fiumicino Airport (FCO)
            (41.7993, 12.5949),  # Ciampino Airport (CIA)
            (41.9029, 12.4534),  # Vatican City
            (41.8902, 12.4922),  # Colosseum area
            (41.9058, 12.4823),  # Spanish Steps/Tridente
            (41.8349, 12.4757),  # EUR District
        ]
        
        center_hexagons = []
        for lat, lng in important_centers:
            h3_index = self._get_h3_index(lat, lng)
            # Only add if this hexagon exists in our districts
            if h3_index in self.districts:
                center_hexagons.append(h3_index)
        
        weights = {}
        for hexagon in self.districts:
            max_weight = 1
            if hexagon in weights:
                max_weight = weights[hexagon]
                
            for center in center_hexagons:
                # If in Krings
                distance = h3.grid_distance(hexagon, center)
                # Center: 5, 1-ring: 4, 2-ring: 3, 3-ring: 2, 4-ring: 1, 5+ rings: 1
                if distance == 0:
                    weight = 5
                elif distance <= 4:
                    weight = 5 - distance
                else:
                    weight = 1
                
                # Keep the maximum weight from all centers
                max_weight = max(max_weight, weight)
            weights[hexagon] = max_weight
        return weights
    
            
        

if __name__ == "__main__":
    map_data = MapData()
    df = pd.DataFrame(map_data.hexagon_weights.items(), columns=['district', 'weight'])
    df.to_csv('data/databases/hexagons.csv', index=False)
    print(len(map_data.districts))