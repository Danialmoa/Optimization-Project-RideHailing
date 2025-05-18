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
- Data structures: Graph representation of city network