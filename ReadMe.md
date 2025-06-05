# Ride-Hailing Revenue Optimization via Integer Linear Programming

## Project Overview
This project models the problem of a ride-hailing driver choosing rides to maximize revenue using Integer Linear Programming (ILP). The goal is to determine the optimal sequence of rides a driver should accept within their working time constraints to maximize total revenue.


## Problem Description
- Each ride is characterized by:
  - Start and end locations
  - Duration
  - Expected revenue
  - Availability time window
- The driver starts at a fixed location and has a limited working time
- "Deadhead" moves (traveling without passengers) incur costs
- All parameters are deterministic (no uncertainty)

## Methodology
We formulate the ride selection problem using binary decision variables to represent whether a specific ride is chosen or not. Constraints include:
- Time limitations (working hours)
- Ride availability windows
- Spatial constraints (being at the right place at the right time)
- Driver requirements (breaks, starting location)

The resulting ILP problem is solved using Gurobi optimizer.

## Development Roadmap
1. Basic ride selection with time limit
2. Add negative-cost deadhead moves
3. Add ride availability time windows
4. Include realistic constraints (breaks, start node)
5. Test on real city data

## Expected Outcomes
This model provides:
- A computational framework for optimal ride selection
- Insights into revenue maximization strategies
- Scalability from small test graphs to real-world city networks
- A foundation for potential extensions

## Implementation Details
- Programming language: Python
- Solver: Gurobi


## Project Structure
```
├── data/ # All simulation code for generating Ride & Map data
├── models/ # Ride & Map and Driver module implementations
├── main.py # Main optimization script
└── outputs/ # Results and output files
```

## Installation & Setup
1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Ensure Gurobi is properly installed and licensed

## Usage
Run the main optimization:
```bash
python main.py
```

## Results & Visualizations
The project includes comprehensive analysis and visualizations:
- Route visualization on Rome city map
- Revenue optimization comparisons

**Note:** Presentation slides and detailed visualizations are available in the project repository.


**Course Context:** This project is part of the Optimization course at Siena University.
