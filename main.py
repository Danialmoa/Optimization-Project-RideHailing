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

        # Binary variable: 1 if driver moves empty from district i to j after ride r
        # Only 2-ring neighbors are considered -> For guorabi limitation
        self.move_without_ride = self.model.addVars(
            [(r, i, j) for r in self.rides + ['start'] 
             for i in self.map.districts for j in self.map.get_neighbors(i) if i != j],
            vtype=gp.GRB.BINARY,
            name="move_without_ride"
        ) # all possible moves after a ride
        
        # Time when ride r starts
        self.ride_start_time = self.model.addVars(
            self.rides,
            lb=0,
            ub=self.drivers.end_time,
            vtype=gp.GRB.CONTINUOUS,
            name="ride_start_time"
        )
        # Arrival time
        self.arrival_time = self.model.addVars(
            self.map.districts, 
            lb=self.drivers.start_time, 
            ub=self.drivers.end_time, 
            vtype=gp.GRB.CONTINUOUS, 
            name="arrival_time"
        )
        # Departure time
        self.departure_time = self.model.addVars(
            self.map.districts, 
            lb=self.drivers.start_time, 
            ub=self.drivers.end_time, 
            vtype=gp.GRB.CONTINUOUS, 
            name="departure_time"
        )
        # Wait time
        self.wait_time = self.model.addVars(
            self.map.districts, 
            lb=0, 
            ub=self.drivers.end_time-self.drivers.start_time, 
            vtype=gp.GRB.CONTINUOUS, 
            name="wait_time"
        )
        number_of_total_variables = len(self.ride_sequence) + len(self.move_without_ride) + len(self.ride_start_time) + len(self.arrival_time) + len(self.departure_time) + len(self.wait_time)
        print(f"Number of total variables: {number_of_total_variables}")
              
    def _add_constraints(self):
        # Define a large constant for big-M constraints
        M = 10000
        
        # 1. Each ride can be taken at most once (optional)
        for r in self.rides:
            self.model.addConstr(
                gp.quicksum(self.ride_sequence[s, r] for s in self.rides + ['start'] if s != r) <= 1
            )
        
        # 2. Flow conservation - if a driver arrives somewhere, they must leave
        for s in self.rides:
            # If ride s is taken, driver must either take another ride or move empty
            # Only 2-ring neighbors are considered
            outgoing_rides = gp.quicksum(self.ride_sequence[s, r] for r in self.rides if r != s)
            valid_empty_moves = gp.quicksum(
                self.move_without_ride[s, s.destination, j] 
                for j in self.map.get_neighbors(s.destination) if j != s.destination
            )
            taken = gp.quicksum(self.ride_sequence[prev, s] for prev in self.rides + ['start'] if prev != s)
            self.model.addConstr(outgoing_rides + valid_empty_moves == taken)
        
        # 3. Driver starts at their start location
        start_rides = gp.quicksum(
            self.ride_sequence['start', r] for r in self.rides if r.origin == self.drivers.start_location
        )
        valid_start_moves = gp.quicksum(
            self.move_without_ride['start', self.drivers.start_location, j] 
            for j in self.map.get_neighbors(self.drivers.start_location) if j != self.drivers.start_location
        )
        self.model.addConstr(start_rides + valid_start_moves == 1)
        
        # 4. Driver must end at their end location
        # for r in self.rides:
        #     # If it's the last ride, ensure it ends at the driver's end location
        #     if r.destination != self.drivers.end_location:
        #         self.model.addConstr(
        #             gp.quicksum(self.ride_sequence[s, r] for s in self.rides + ['start'] if s != r) <=
        #             self.move_without_ride[r, r.destination, self.drivers.end_location]
        #         )
        
        # 5. Time window constraints for rides
        for r in self.rides:
            # Only enforce time windows for taken rides
            taken = gp.quicksum(self.ride_sequence[s, r] for s in self.rides + ['start'] if s != r)
            self.model.addConstr(self.ride_start_time[r] >= r.available_at - M * (1 - taken))
            self.model.addConstr(self.ride_start_time[r] <= r.end_at + M * (1 - taken))
        
        # 6. Time continuity constraints
        # If ride s is followed by ride r, ensure enough time between them
        for s in self.rides:
            for r in self.rides:
                if s != r:
                    # Time to go from s.destination to r.origin + waiting time
                    travel_time = self.map.get_time(s.destination, r.origin)
                    self.model.addConstr(
                        self.ride_start_time[r] >= 
                        self.ride_start_time[s] + s.duration + travel_time - M * (1 - self.ride_sequence[s, r])
                    )
        
        # 7. Start time constraint for the first ride
        for r in self.rides:
            # If r is the first ride
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
        
        # 9. Ensure proper sequencing from empty moves
        for r in self.rides + ['start']:
            for i in self.map.districts:
                for j in self.map.get_neighbors(i):
                    # Only create constraint if this variable exists
                    if (r, i, j) in self.move_without_ride:
                        valid_next_rides = [next_r for next_r in self.rides if next_r.origin == j and r != next_r]
                        if valid_next_rides:
                            self.model.addConstr(
                                self.move_without_ride[r, i, j] <= 
                                gp.quicksum(self.ride_sequence[r, next_r] for next_r in valid_next_rides)
                            )


    def optimize(self):
        self._add_variables()
        self._add_constraints()
        
        self.model.setObjective(
            gp.quicksum(
                self.ride_sequence[s, r] * r.price for s in self.rides + ['start'] for r in self.rides if s != r
            ),
            gp.GRB.MAXIMIZE
        )
        
        self.model.setParam('LogToConsole', 1) # show log in console
        self.model.setParam('DisplayInterval', 10) # update every 10 seconds
        
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
                    if j == self.drivers.end_location:
                        if self.move_without_ride[current, current_location, j].x > 0.5:
                            travel_time = self.map.get_time(current_location, j)
                            total_cost += self.map.get_cost(current_location, j)
                            report_text += f"Empty move from {current_location} to {j} at time {current_time} (duration: {travel_time}, cost: {self.map.get_cost(current_location, j)})\n"
                            current_time += travel_time
                            current_location = j
                            break   
                break
            
            # If origin is different from current location, need empty movement
            if next_ride.origin != current_location:
                travel_time = self.map.get_time(current_location, next_ride.origin)
                total_cost += self.map.get_cost(current_location, next_ride.origin)
                report_text += f"Empty move from {current_location} to {next_ride.origin} at time {current_time} (duration: {travel_time}, cost: {self.map.get_cost(current_location, next_ride.origin)})\n"
                current_time = current_time + travel_time
                current_location = next_ride.origin
            
            # Take the ride
            ride_start = self.ride_start_time[next_ride].x
            wait_time = round(ride_start - current_time, 2)
            if wait_time > 0:
                report_text += f"Wait at location {current_location} for {wait_time} time units\n"
            
            report_text += f'Ride from {next_ride.origin} to {next_ride.destination} starts at {ride_start:.2f}, ends at {ride_start + next_ride.duration:.2f} (revenue: {next_ride.price})\n'
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
        return total_revenue - total_cost

def main():
    rides = pd.read_csv('data/databases/rides.csv')
    rides = [Ride(**ride) for ride in rides.to_dict(orient='records')]

    # start from 8 to 22
    driver = Driver(start_time=8 * 60, end_time=22 * 60, start_location='871e80420ffffff', end_location='871e80420ffffff')
    map = Map()
    
    optimizer = OptimizerModel(rides, driver, map)
    optimizer.optimize()
    optimizer.get_results()
    
if __name__ == "__main__":
    main()
    