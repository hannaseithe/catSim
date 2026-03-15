# 2. Separate simulation engine from Django persistence and API layer

Date: 2026-11-01

## Status

Accepted

## Context

We need to define how the simulation engine, persistence layer, and API layer interact and maintain separation of concerns.

## Decision Drivers

As part of this practice project, I wanted a clean, production-level architecture with clear separation of concerns.  
This design approach was suggested during a brainstorming session with GPT.

## Considered Options

Initially I imagined the simulation engine to be tightly coupled with the Django persistence layer. 

## Decision

The simulation engine will be implemented as pure Python, independent of Django or any web framework.  
The persistence and API layers will be implemented in Django and Django REST Framework, respectively.

[Simulation Engine] <-> [Persistence Layer / Django Models] <-> [API Layer / DRF]

## Consequences

- This will allow to test the simulation engine in isolation 
- swap the django layer out for different frameworks later
- data exchanged between simulation and persistence/API will need to be serialized
