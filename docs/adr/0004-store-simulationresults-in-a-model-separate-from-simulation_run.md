# 4. Store Simulation Results in a Dedicated Model Separate from SimulationRun

Date: 2026-01-11

## Status
Accepted

## Context
Simulations require storing both metadata (status, parameters, error messages, etc.) during execution,  
and large, data-rich result objects after successful completion.  
A decision was needed on how to structure the database models to handle these requirements efficiently.

## Decision Drivers
- There is a one-to-one relationship between a simulation run and its results  
- The results field is very data-intensive and should only be queried when needed

## Considered Options
- Keep all data in a single model/table

## Decision
Split the data into two models: `SimulationRun` and `SimulationResult`,  
with a OneToOneField linking `SimulationResult` to `SimulationRun`.

## Consequences
- Accessing simulation results requires a join between the two tables  
- Queries for metadata only (status, error messages, run parameters) do not touch the large `SimulationResult` table, improving performance
