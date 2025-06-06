import gurobipy as gp
import numpy as np
import pandas as pd

from models.ride import Ride
from models.map import Map
from models.driver import Driver


class OptimizerModel:
    def __init__(self, rides, drivers, map):
        self.rides = rides
        self.drivers = drivers
        self.map = map
        
        self.model = gp.Model("Ride-Hailing Revenue Optimization")
        
    def _add_variables(self):
        # Binary variable: 1 if driver takes ride r immediately after ride s (or start)
        self.ride_sequence = self.model.addVars(
            [(s, r) for s in self.rides + ['start'] for r in self.rides if s != r],
            vtype=gp.GRB.BINARY,
            name="ride_sequence"
        ) # First index is the previous ride, second index is the current ride
        print(f"Number of ride_sequence variables: {len(self.ride_sequence)}")
        
        feasible_moves = []
        
        for r in self.rides + ['start']:
            if r == 'start':
                driver_location = self.drivers.start_location
            else:
                driver_location = r.destination
            
            for neighbor in self.map.get_neighbors(driver_location):
                if neighbor != driver_location:
                    feasible_moves.append((r, driver_location, neighbor))
        
        self.move_without_ride = self.model.addVars(
            feasible_moves,
            vtype=gp.GRB.BINARY,
            name="move_without_ride"
        )
        print(f"Number of move_without_ride variables: {len(self.move_without_ride)}")
        
        # Time when ride r starts
        self.ride_start_time = self.model.addVars(
            self.rides,
            lb=0,
            ub=self.drivers.end_time,
            vtype=gp.GRB.CONTINUOUS,
            name="ride_start_time"
        )

        number_of_total_variables = len(self.ride_sequence) + len(self.move_without_ride) + len(self.ride_start_time)
        print(f"Number of total variables: {number_of_total_variables}")
              
    def _add_constraints(self):
        # Define a large constant for big-M constraints
        M = 10000
        
        # 1. Spatial constraint: Can only take rides from current location
        # For rides taken immediately after start
        for r in self.rides:
            if r.origin != self.drivers.start_location:
                # If we take ride r after start, we must have moved empty to r.origin first
                empty_move_to_origin = gp.quicksum(
                    self.move_without_ride['start', self.drivers.start_location, r.origin]
                    for key in self.move_without_ride.keys()
                    if key == ('start', self.drivers.start_location, r.origin)
                )
                self.model.addConstr(self.ride_sequence['start', r] <= empty_move_to_origin)
        
        # For rides taken after other rides  
        for s in self.rides:
            for r in self.rides:
                if s != r and s.destination != r.origin:
                    # If we take ride r after ride s, we must have moved empty from s.destination to r.origin
                    empty_move_to_origin = gp.quicksum(
                        self.move_without_ride[s, s.destination, r.origin]
                        for key in self.move_without_ride.keys() 
                        if key == (s, s.destination, r.origin)
                    )
                    self.model.addConstr(self.ride_sequence[s, r] <= empty_move_to_origin)
        
        # 2. Flow conservation - if driver arrives somewhere, they must leave
        for s in self.rides:
            outgoing_rides = gp.quicksum(self.ride_sequence[s, r] for r in self.rides if r != s)
            valid_empty_moves = gp.quicksum(
                self.move_without_ride[s, s.destination, j] 
                for j in self.map.get_neighbors(s.destination) 
                if j != s.destination and (s, s.destination, j) in self.move_without_ride
            )
            taken = gp.quicksum(self.ride_sequence[prev, s] for prev in self.rides + ['start'] if prev != s)
            self.model.addConstr(outgoing_rides + valid_empty_moves == taken)
        
        # 3. Driver starts at their start location  
        start_rides = gp.quicksum(
            self.ride_sequence['start', r] for r in self.rides if r.origin == self.drivers.start_location
        )
        valid_start_moves = gp.quicksum(
            self.move_without_ride['start', self.drivers.start_location, j] 
            for j in self.map.get_neighbors(self.drivers.start_location) 
            if j != self.drivers.start_location and ('start', self.drivers.start_location, j) in self.move_without_ride
        )
        self.model.addConstr(start_rides + valid_start_moves == 1)
        
        # 4. Each empty move can only be used once
        for (r, i, j) in self.move_without_ride.keys():
            # An empty move can only happen if we're at location i after ride r
            if r == 'start':
                available = 1 if i == self.drivers.start_location else 0
            else:
                available = 1 if i == r.destination else 0
                available *= gp.quicksum(self.ride_sequence[prev, r] for prev in self.rides + ['start'] if prev != r)
            
            self.model.addConstr(self.move_without_ride[r, i, j] <= available)
        
        # 5. Time window constraints for rides
        for r in self.rides:
            taken = gp.quicksum(self.ride_sequence[s, r] for s in self.rides + ['start'] if s != r)
            self.model.addConstr(self.ride_start_time[r] >= r.available_at - M * (1 - taken))
            self.model.addConstr(self.ride_start_time[r] <= r.end_at + M * (1 - taken))
        
        # 6. Time continuity constraints
        for s in self.rides:
            for r in self.rides:
                if s != r:
                    travel_time = self.map.get_time(s.destination, r.origin)
                    self.model.addConstr(
                        self.ride_start_time[r] >= 
                        self.ride_start_time[s] + s.duration + travel_time - M * (1 - self.ride_sequence[s, r])
                    )
        
        # 7. Start time constraint for the first ride
        for r in self.rides:
            travel_time = self.map.get_time(self.drivers.start_location, r.origin)
            self.model.addConstr(
                self.ride_start_time[r] >= 
                self.drivers.start_time + travel_time - M * (1 - self.ride_sequence['start', r])
            )
        
        # 8. End time constraint
        for r in self.rides:
            # Ensure driver can return to end location on time
            travel_time = self.map.get_time(r.destination, self.drivers.end_location)
            self.model.addConstr(
                self.ride_start_time[r] + r.duration + travel_time <= 
                self.drivers.end_time + M * (1 - gp.quicksum(self.ride_sequence[s, r] for s in self.rides + ['start'] if s != r))
            )
        


    def optimize(self):
        self._add_variables()
        self._add_constraints()
        
        # Revenue
        ride_profit = gp.quicksum(
            self.ride_sequence[s, r] * (r.price - self.map.get_cost(r.origin, r.destination)) 
            for s in self.rides + ['start'] for r in self.rides if s != r
        )

        # Empty move cost
        empty_move_cost = gp.quicksum(
            self.move_without_ride[r, i, j] * self.map.get_cost(i, j)
            for (r, i, j) in self.move_without_ride.keys()
        )

        self.model.setObjective(ride_profit - empty_move_cost, gp.GRB.MAXIMIZE)
        
        
        self.model.setParam('NodefileStart', 0.1)
        self.model.setParam('NodefileDir', '/tmp')
        
        self.model.setParam('LogToConsole', 1) # show log in console
        self.model.setParam('DisplayInterval', 10) # update every 10 seconds
        self.model.setParam('MIPGap', 0.01) 
        self.model.setParam('TimeLimit', 3600)
        
        self.model.update()
        self.model.optimize()
        self.model.write("outputs/model.lp")
        
    def get_results(self):
        # Check if the model has been solved
        if self.model.status != gp.GRB.OPTIMAL:
            print(f"Model status: {self.model.status}")
            return
        
        report_text = ""
        
        # Total revenue and cost
        total_revenue = 0
        total_cost = 0
        
        # Find the first ride or movement
        current = 'start'
        current_location = self.drivers.start_location
        current_time = self.drivers.start_time
        
        report_text += "\n=== DRIVER ITINERARY ===\n"
        report_text += f"Start at location {current_location} at time {current_time}\n"
        
        data_frame = pd.DataFrame()
        
        # Follow the sequence of rides and movements
        while True:
            # Find next ride
            next_ride = None
            for r in self.rides:
                if current != r and self.ride_sequence[current, r].x > 0.5:
                    next_ride = r
                    break
            
            if next_ride is None:
                # No more rides, check for empty movement to end location
                for j in self.map.get_neighbors(current_location):
                    if (j == self.drivers.end_location and 
                        (current, current_location, j) in self.move_without_ride and
                        self.move_without_ride[current, current_location, j].x > 0.5):
                        travel_time = self.map.get_time(current_location, j)
                        total_cost += self.map.get_cost(current_location, j)
                        report_text += f"Empty move from {current_location} to {j} at time {current_time} (duration: {travel_time}, cost: {self.map.get_cost(current_location, j)})\n"
                        data_frame = pd.concat([data_frame, pd.DataFrame({
                            'movement_type': ['empty_move'],
                            'hexagon_origin': [current_location],
                            'lat_origin': [self.map.get_lat(current_location)],
                            'lng_origin': [self.map.get_lng(current_location)],
                            'hexagon_destination': [j],
                            'lat_destination': [self.map.get_lat(j)],
                            'lng_destination': [self.map.get_lng(j)],
                            'start_at': [current_time],
                            'end_at': [current_time + travel_time],
                            'duration': [travel_time],
                            'revenue': [0],
                            'cost': [self.map.get_cost(current_location, j)]
                        })], ignore_index=True)

                        current_time += travel_time
                        current_location = j
                        break   
                break
            
            # If origin is different from current location, need empty movement
            if next_ride.origin != current_location:
                # Check if this move was actually planned in the optimization
                move_found = False
                for (r, i, j) in self.move_without_ride.keys():
                    if (r == current and i == current_location and j == next_ride.origin and 
                        self.move_without_ride[r, i, j].x > 0.5):
                        travel_time = self.map.get_time(current_location, next_ride.origin)
                        total_cost += self.map.get_cost(current_location, next_ride.origin)
                        report_text += f"Empty move from {current_location} to {next_ride.origin} at time {current_time} (duration: {travel_time}, cost: {self.map.get_cost(current_location, next_ride.origin)})\n"
                        data_frame = pd.concat([data_frame, pd.DataFrame({
                            'movement_type': ['empty_move'],
                            'hexagon_origin': [current_location],
                            'lat_origin': [self.map.get_lat(current_location)],
                            'lng_origin': [self.map.get_lng(current_location)],
                            'hexagon_destination': [next_ride.origin],
                            'lat_destination': [self.map.get_lat(next_ride.origin)],
                            'lng_destination': [self.map.get_lng(next_ride.origin)],
                            'start_at': [current_time],
                            'end_at': [current_time + travel_time],
                            'duration': [travel_time],
                            'revenue': [0],
                            'cost': [self.map.get_cost(current_location, next_ride.origin)]
                        })], ignore_index=True)
                        
                        current_time = current_time + travel_time
                        current_location = next_ride.origin
                        move_found = True
                        break
                
            
            # Take the ride
            ride_start = self.ride_start_time[next_ride].x
            wait_time = round(ride_start - current_time, 2)
            if wait_time > 0:
                report_text += f"Wait at location {current_location} for {wait_time} time units\n"
                data_frame = pd.concat([data_frame, pd.DataFrame({
                    'movement_type': ['wait'],
                    'hexagon_origin': [current_location],
                    'lat_origin': [self.map.get_lat(current_location)],
                    'lng_origin': [self.map.get_lng(current_location)],
                    'hexagon_destination': [current_location],
                    'lat_destination': [self.map.get_lat(current_location)],
                    'lng_destination': [self.map.get_lng(current_location)],
                    'start_at': [current_time],
                    'end_at': [current_time + wait_time],
                    'duration': [wait_time],
                    'revenue': [0],
                    'cost': [0]
                })], ignore_index=True)
            
            report_text += f'Ride from {next_ride.origin} to {next_ride.destination} starts at {ride_start:.2f}, ends at {ride_start + next_ride.duration:.2f} (revenue: {next_ride.price})\n'
            data_frame = pd.concat([data_frame, pd.DataFrame({
                'movement_type': ['ride'],
                'hexagon_origin': [next_ride.origin],
                'lat_origin': [self.map.get_lat(next_ride.origin)],
                'lng_origin': [self.map.get_lng(next_ride.origin)],
                'hexagon_destination': [next_ride.destination],
                'lat_destination': [self.map.get_lat(next_ride.destination)],
                'lng_destination': [self.map.get_lng(next_ride.destination)],
                'start_at': [ride_start],
                'end_at': [ride_start + next_ride.duration],
                'duration': [next_ride.duration],
                'revenue': [next_ride.price],
                'cost': [self.map.get_cost(next_ride.origin, next_ride.destination)]
            })], ignore_index=True)
                        
            total_revenue += next_ride.price
            total_cost += self.map.get_cost(current_location, next_ride.origin)
            
            current_time = ride_start + next_ride.duration
            current_location = next_ride.destination
            current = next_ride
        
        report_text += "\n=== SUMMARY ===\n"
        report_text += f"Total revenue: {total_revenue}\n"
        report_text += f"Total empty movement cost: {total_cost}\n"
        report_text += f"Net profit: {total_revenue - total_cost}\n"
        
        with open('outputs/report.txt', 'w') as f:
            f.write(report_text)
        data_frame.to_csv('outputs/data_frame.csv', index=False)
        return data_frame

def main():
    rides = pd.read_csv('data/databases/rides.csv')
    rides = [Ride(**ride) for ride in rides.to_dict(orient='records')]

    # start from 8 to 22
    driver = Driver(start_time=8 * 60, end_time=22 * 60, start_location='871e80420ffffff', end_location='871e80420ffffff')
    map = Map()
    
    optimizer = OptimizerModel(rides, driver, map)
    optimizer.optimize()
    optimizer.get_results()
    
    
def greedy_solution():
    # select highest price in each time (without moving empty)
    rides = pd.read_csv('data/databases/rides.csv')
    driver = Driver(start_time=8 * 60, end_time=22 * 60, start_location='871e80420ffffff', end_location='871e80420ffffff')
    map = Map()
    
    s_time = driver.start_time
    current_location = driver.start_location
    selected_rides = []
    while s_time < driver.end_time:
        available_rides = rides[rides['origin'] == current_location]
        available_rides = available_rides[available_rides['available_at'] <= s_time]
        available_rides = available_rides[available_rides['end_at'] >= s_time]
        available_rides = available_rides[available_rides['price'] > 0]
        if len(available_rides) > 0:
            best_ride = available_rides.sort_values(by='price', ascending=False).iloc[0]
            print(best_ride)
            s_time += best_ride['duration']
            current_location = best_ride['destination']
            selected_rides.append(best_ride)
            print(f"Ride from {best_ride['origin']} to {best_ride['destination']} starts at {s_time}, ends at {s_time + best_ride['duration']} (revenue: {best_ride['price']}, cost: {map.get_cost(best_ride['origin'], best_ride['destination'])})")
        else:
            s_time += 1
    print(pd.DataFrame(selected_rides))
    print(f"Total revenue: {sum([ride['price'] for ride in selected_rides])}")
    print(f"Total cost: {sum([map.get_cost(ride['origin'], ride['destination']) for ride in selected_rides])}")
    print(f"Net profit: {sum([ride['price'] for ride in selected_rides]) - sum([map.get_cost(ride['origin'], ride['destination']) for ride in selected_rides])}")
    
if __name__ == "__main__":
    #main()
    greedy_solution()
    