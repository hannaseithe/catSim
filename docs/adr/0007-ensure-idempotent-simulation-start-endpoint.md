# 7. Ensure Idempotent Simulation Start Endpoint

Date: 2026-02-19

## Status
Accepted

## Context
The simulation start endpoint may be called multiple times by clients due to network retries or user error.  
Without idempotency, this could result in multiple simulation runs for the same parameters, wasting resources and potentially producing inconsistent results.

## Decision Drivers

- Ensure API reliability and consistency  
- Prevent duplicate simulation runs for the same request and ensure data integrity
- Simplify client-side handling in case of retries

## Considered Options

- Allow multiple simulation runs for each request (no idempotency)  
- Enforce idempotent behavior through adding UUID (chosen)
- Enforce idempotent behavior based on parameters (difficult as the simulation contains stochastic noise)

## Decision

A UUID field was added to simulation start request and to the `SimulationRun` model. The client-side generated UUID, will guarantee a simulation with the same uuid is not queued more than once (as could during network retries)

## Consequences

- Prevents duplicate simulation runs  
- Clients can safely retry requests without risking multiple executions  
- Requires generating and tracking uuids for each simulation request
- Simulations started with identical parameters but different UUID will all run, especially as the results are expected to be different because of stochastic noise