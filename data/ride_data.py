import pandas as pd
import numpy as np
import random

from models.ride import Ride

class RideData:
    def __init__(self):
        self.hexagons = pd.read_csv('data/databases/districts.csv')['district'].tolist()
        self.distance_matrix = np.load('data/databases/distance_matrix.npy')
        self.h3_to_index = {h3_index: i for i, h3_index in enumerate(self.hexagons)}
        self.start_time = 8 # 8:00 AM
        self.end_time = 23 # 11:00 PM
        
        # https://www.archeoroma.org/taxi/rates/
        self.price_per_km_range = (1.1, 1.6) # 1.1 - 1.6 EUR/km
        self.initial_fare = 3 # 3 EUR
        self.average_speed_range = (15, 25) # 15 - 25 km/h
    
    @property
    def generate_rides(self):
        origin_hexagon = random.choice(self.hexagons)
        destination_hexagon = random.choice(self.hexagons)
        while origin_hexagon == destination_hexagon:
            destination_hexagon = random.choice(self.hexagons)
            
        available_at = random.randint(self.start_time, self.end_time)
        end_at = random.randint(available_at, self.end_time)
        
        distance = self.distance_matrix[self.h3_to_index[origin_hexagon], self.h3_to_index[destination_hexagon]] * 1.3 # 1.3 is approxiation ratio for air distance to road distance
        duration = distance / random.uniform(self.average_speed_range[0], self.average_speed_range[1]) * 60 # minutes
        price = self.initial_fare + distance * random.uniform(self.price_per_km_range[0], self.price_per_km_range[1])
        
        return Ride(origin_hexagon, destination_hexagon, available_at, end_at, price, duration)
    
    
if __name__ == "__main__":
    ride_data = RideData()
    print(ride_data.generate_rides)
    