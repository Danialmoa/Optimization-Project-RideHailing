import pandas as pd
import numpy as np
import random

from models.ride import Ride

class RideData:
    def __init__(self):
        self.data = pd.read_csv('data/databases/hexagons.csv')
        self.hexagons = self.data['district'].tolist()
        self.hexagon_weights = self.data['weight'].tolist()
        self.distance_matrix = np.load('data/databases/distance_matrix.npy')
        self.h3_to_index = {h3_index: i for i, h3_index in enumerate(self.hexagons)}
        self.start_time = 8 * 60 # 8:00 AM (converted to minutes)
        self.end_time = 23 * 60 # 11:00 PM (converted to minutes)
        
        # https://www.archeoroma.org/taxi/rates/
        self.price_per_km_range = (1.1, 1.6) # 1.1 - 1.6 EUR/km
        self.initial_fare = 3 # 3 EUR
        self.average_speed_range = (15, 25) # 15 - 25 km/h
    
    @property
    def generate_rides(self):
        origin_hexagon = random.choices(self.hexagons, weights=self.hexagon_weights, k=1)[0]
        destination_hexagon = random.choices(self.hexagons, weights=self.hexagon_weights, k=1)[0]
        while origin_hexagon == destination_hexagon:
            destination_hexagon = random.choices(self.hexagons, weights=self.hexagon_weights, k=1)[0]
            
        available_at = random.randint(self.start_time, self.end_time - 1)
        end_at = random.randint(available_at + 1, self.end_time)
        
        distance = self.distance_matrix[self.h3_to_index[origin_hexagon], self.h3_to_index[destination_hexagon]] * 1.3 # 1.3 is approxiation ratio for air distance to road distance
        duration = distance / random.uniform(self.average_speed_range[0], self.average_speed_range[1]) * 60 # minutes
        price = self.initial_fare + distance * random.uniform(self.price_per_km_range[0], self.price_per_km_range[1])
        
        return Ride(origin_hexagon, destination_hexagon, available_at, end_at, price, duration)
    
    
if __name__ == "__main__":
    ride_data = RideData()
    rides = [ride_data.generate_rides for _ in range(1500)]
    df = pd.DataFrame(
        [ride.to_dict() for ride in rides],
        columns=['origin', 'destination', 'available_at', 'end_at', 'price', 'duration']
    )
    df.to_csv('data/databases/rides.csv', index=False)
    