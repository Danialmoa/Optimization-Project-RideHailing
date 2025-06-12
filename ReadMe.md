# Ride-Hailing Revenue Optimization using Integer Linear Programming (ILP)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Danialmoa/Optimization-Project-RideHailing/blob/main/notebooks/colab_run.ipynb)

## Overview

This project uses Integer Linear Programming (ILP) to help a ride-hailing driver in Rome select the most profitable sequence of rides within a workday. Given a set of ride requests, driver constraints (time/location), and map-based distances, the system finds the optimal ride plan that maximizes net profit (revenue - cost of empty travel).

## Folder Structure

```
Optimization-RideHailing/
│
├── Data/
│   ├── Map_data.py             # Generates hexagonal zones & distance matrix
│   ├── Ride_data.py            # Generates 100 simulated ride requests
│   └── databases/
│       ├── taxi_data_subset.csv       # Sample taxi data from Rome
│       ├── hexagons.csv               # List of hexagonal zones with demand weights
│       ├── distance_matrix.npy        # Distance matrix between zones (in km)
│       └── rides.csv                  # Generated ride dataset
│
├── Models/
│   ├── Driver.py              # Driver data model (start/end time, location)
│   ├── Map.py                 # Encapsulates distance, cost, time, and neighbors logic
│   └── Ride.py                # Ride data model (location, time, price, etc.)
│
├── main.py                    # Main optimization logic (to be implemented)
└── README.md                  # Project documentation (this file)
```

## Detailed File Descriptions

### Data/Map_data.py
- Reads GPS-based taxi data and transforms coordinates into H3 hexagons.
- Calculates:
  - Demand weight per hexagon based on proximity to major landmarks (e.g., Termini, Vatican, airports).
  - Pairwise distance matrix between all hexagons using the H3 system.

**Output:**
- `hexagons.csv` — list of H3 cell IDs and their weights.
- `distance_matrix.npy` — distance between all pairs of hexagons.

### Data/Ride_data.py
- Randomly generates 100 ride requests based on the weight distribution (demand).
- Each ride contains:
  - Origin and destination hexagons.
  - Availability time and end time (in minutes).
  - Ride price (base fare + distance-based fare).
  - Duration (based on estimated speed).

**Important logic:**
- Origins and destinations are sampled randomly but weighted by demand.
- Distance is scaled by `1.3` to approximate road distance.
- Speed randomly chosen in `[15, 25] km/h`.
- Price = base fare (`3 EUR`) + distance × per-km fare (`[1.1–1.6] EUR/km`).

**Output:**
- `rides.csv` — a list of generated ride requests.

### Models/Driver.py

```python
class Driver:
    def __init__(self, start_time, end_time, start_location, end_location):
        self.start_time = start_time
        self.end_time = end_time
        self.start_location = start_location
        self.end_location = end_location
```

- Represents a driver.
- Includes working time window (`start_time`, `end_time`) and starting/ending hexagon locations.

### Models/Ride.py
- Data class for storing all info about a ride.
- Contains methods:
  - `to_dict()` for exporting ride info including lat/lng coordinates using H3.

```python
class Ride:
    def __init__(self, origin, destination, available_at, end_at, price, duration):
        ...
```

**Variables:**
- `origin` / `destination`: H3 cell ID
- `available_at`, `end_at`: time range (in minutes)
- `price`: calculated fare
- `duration`: trip duration (minutes)
- `lng_origin`: Longitude of the center of the origin H3 cell.
- `lat_destination`: Latitude of the destination hexagon.
- `lng_destination`: Longitude of the destination hexagon.

### Models/Map.py
- module provides a map abstraction based on the H3 spatial indexing system.
- Handles operations like:
  - Get distance between two hexagons.
  - Find neighbors of a hexagon.
  - Estimate cost and duration.
  - Convert H3 cells to lat/lng.

```python
class Map:
    def get_distance(origin, destination) -> float
    def get_time(origin, destination) -> float
    def get_cost(origin, destination) -> float
```

**Approximations:**
- Road distance ≈ Air distance × 1.3 (1.3 is the air-to-road distance approximation)
- Cost = Distance × 1.3 × 0.7 (0.7 is a scaling factor derived from pricing heuristics or estimated cost/km)

### main.py
- This file contains the core optimization logic of the system.

- It takes a list of ride requests, one driver, and a city map then figures out the smartest way to assign rides and plan movements, so the driver earns the maximum possible profit within their working hours.

**What it does:**
- Builds a MILP model using Gurobi
- Decides which rides to take, in what order
- Includes empty moves (without a passenger) if needed
- Handles time windows, ride durations, and travel times
- Schedules exact start times for each ride
- Makes sure everything fits within the driver’s shift

**Objective:**
- Maximize → ride revenue - empty travel cost

## Variables in model

**ride_sequence[s, r]**
- Type: 0 or 1 (binary)
- Meaning: If the driver goes from ride s to ride r, this is 1. Otherwise, it’s 0.
- Purpose: To decide the order of rides.

**move_without_ride[r, i, j]**
- Type: 0 or 1 (binary)
- Meaning: If the driver moves from area i to area j after ride r without a passenger.
- Purpose: To allow empty movements when needed.

**ride_start_time[r]**
- Type: Any number ≥ 0 (continuous)
- Meaning: The time when ride r starts.
- Purpose: To make sure rides happen at the right time and in the right order.

## Constraints in model

**Flow Conservation**
- If the driver finishes a ride, they must either take another ride or move empty to somewhere else.
- Makes sure the driver doesn’t “teleport” and always continues from where they left off.

**Start Location Constraint**
- The first ride (or first empty move) must begin at the driver’s start location.

**Ride Time Windows**
- Every ride has a valid time window (from available_at to end_at).
- If a ride is selected, its start time must stay within that range.

**Ride Order Timing**
- If ride r comes after ride s, there must be enough time to:
- Finish ride s
- Move to the start of ride r
- And maybe wait if needed

**First Ride Timing**
- The first ride (if taken) must start after the driver’s shift begins, with enough travel time from the start location.

**End of Shift**
- After the last ride, the driver must be able to return to their end location before the shift ends.

## Optimization Problem

### Goal:
Maximize total revenue:

$$
\text{Maximize} \sum_{i=1}^{N} x_i \cdot \text{price}_i
$$

### Constraints:
1. **Time Constraint:**  
   A ride `i` can only be accepted if it fits between driver’s working hours.

2. **Non-overlapping Constraint:**  
   Two selected rides cannot overlap in time.

3. **Sequential Compatibility:**  
   The origin of ride `j` must be reachable from the destination of ride `i` within the time window.

4. **Binary Decision Variable:**

Let  
$$
x_i \in \{0, 1\}
$$  
where:  
- \( x_i = 1 \) if ride \( i \) is selected  
- \( x_i = 0 \) otherwise

### Optimizer:
Will use **Integer Linear Programming** (ILP), potentially using solvers like:
- `PuLP` (Python)
- `Google OR-Tools`
- `Gurobi`

## How to Run

1. **Generate Map Data:**
```bash
python Data/Map_data.py
```

2. **Generate Ride Dataset:**
```bash
python Data/Ride_data.py
```

3. *(When optimization logic is added)* Run:
```bash
python main.py
```

## Output Explanation
- Once the optimization script is executed, the following outputs are generated in the outputs/ directory:

 **report.txt:** A detailed textual summary of the driver’s itinerary. This includes:
  - Starting point: location and time
  - Rides: origin, destination, start time, end time, and revenue
  - Waiting periods, if any
  - Empty movements: between districts without passengers (including duration and cost)
  - Summary section:
    - Total revenue
    - Total empty movement cost
    - Net profit

**data_frame.csv:** detailed log of the driver’s actions in CSV format. The main attributes captured are:
  - movement_type: Indicates whether the action is a ride, an empty_move, or a wait.
  - hexagon_origin and hexagon_destination: The H3 index of the starting and ending zones for the action.
  - lat_origin and lng_origin: The latitude and longitude of the origin.
  - lat_destination and lng_destination: The latitude and longitude of the destination.
  - start_at and end_at: The start and end times of the event (in minutes from the beginning of the day).
  - duration: Total duration of the action in minutes.
  - revenue: The income earned (only applicable for rides).
  - cost: The operational cost (applies to both rides and empty moves).

**model.lp:** The full Gurobi optimization model written in LP format.
 - It includes all decision variables, constraints, and the objective function.
 - Use this to inspect the model structure, debug constraint logic, or load the model into Gurobi’s GUI.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Team
- Danial Moafi
- Setareh Soltani
