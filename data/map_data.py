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
        


if __name__ == "__main__":
    map_data = MapData()
    df = pd.DataFrame(map_data.h3_index_to_district.keys(), columns=['district'])
    df.to_csv('data/databases/districts.csv', index=False)
    np.save('data/databases/distance_matrix.npy', map_data.distance_matrix)
    