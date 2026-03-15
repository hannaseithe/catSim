# 3. Execute Simulations Asynchronously Using Celery

Date: 2026-01-11

## Status

Accepted

## Context

Running a simulation can take a significant amount of time. We needed to decide how to implement the endpoint from an API perspective

## Decision Drivers

Simulations are long-running tasks, which suggests an asynchronous API design pattern.  
To allow the API to handle other requests while a simulation is running, and to enable concurrent simulation runs, we needed a suitable solution.

## Considered Options

Basically run the simulation inline and have the server wait for it to finish

## Decision

Simulations are queued and executed through Celery.  
A state management system with endpoints allows clients to check the status of simulation runs.

## Consequences

- Simulations are non-blocking for the API.  
- Clients must poll endpoints to receive simulation results and any errors.  
- Clients may not immediately get results as soon as they become available.
