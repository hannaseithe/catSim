# Cat Simulation Project

I simulate the relationships of cats developing over time. Currently this serves mainly the purpose of practicing headless Django with a fun little simulation behind it

### v1:
- `/simulation` contains the actual simulation, decoupled from django
- `/cats` is the django app, that contains:
  - Basic models for Simulation Run and Results persistence
  - Management command: `python manage.py run_simulation`
  - Celery task: `run_simulation`

- Redis required as Celery broker

### v2:
- the simulation is now accessible through an API, with JWT based authentication:
  - `/api/simulations/`:`GET` -> Get List of Simulations is returned (for normal users only Simulations that they created, and for admin all simulations)
  - `/api/simulations/start/`:`POST` -> Start a simulation (queued with Celery)
  - `/api/simulations/<id>/`:`GET` -> Get Simulation with status and params
  - `/api/simulations/<id>/results/`:`GET` -> Get Simulation results if finished
  - `/api/simulations/<id>/`:`GET` -> Get Simulation error if failed
 
- for authentication:
  -  `/api/token/`:`POST`-> Get Access Token / Login
  -  `/api/token/refresh`:`POST` -> Refresh Token
