import pandas as pd
import numpy as np
import h3

class Map:
    def __init__(self):
        try:
            self.data = pd.read_csv('data/databases/hexagons.csv')
            self.districts = self.data['district'].tolist()
            self.distance_matrix = np.load('data/databases/distance_matrix.npy')
            self.hexagon_weights = self.data['weight'].tolist()
            self.neighbors = self._find_neighbors()
        except Exception as e:
            print(f"Error loading map data, Please run data/map_data.py to generate the data")
            raise e
        
    def _find_neighbors(self):
        neighbors = {}
        for i in range(len(self.districts)):
            neighbors[self.districts[i]] = list(h3.grid_ring(self.districts[i], 2))
        return neighbors
    
    def get_distance(self, origin, destination):
        return self.distance_matrix[self.districts.index(origin), self.districts.index(destination)]
    
    def get_hexagon_weight(self, hexagon):
        return self.hexagon_weights[hexagon]
    
    def get_cost(self, origin, destination):
         # 1.3 is approxiation ratio for air distance to road distance, 0.7 is a factor for the cost of the ride
        return self.distance_matrix[self.districts.index(origin), self.districts.index(destination)] * 1.3 * 0.7
    
    def get_neighbors(self, hexagon):
        return self.neighbors[hexagon]
        
    def get_time(self, origin, destination):
        return self.distance_matrix[self.districts.index(origin), self.districts.index(destination)] * 1.3
    
    def get_lat(self, hexagon):
        return h3.cell_to_latlng(hexagon)[1]
    
    def get_lng(self, hexagon):
        return h3.cell_to_latlng(hexagon)[0]
    
if __name__ == "__main__":
    map = Map()
    
    print(map.get_lat(map.districts[0]))
    print(map.get_lng(map.districts[0]))