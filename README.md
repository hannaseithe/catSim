# Cat Simulation Project

I simulate the relationships of cats developing over time. Currently this serves mainly the purpose of practicing headless Django with a fun little simulation behind it

### [v1.0.0](https://github.com/hannaseithe/catSim/releases/tag/v1.0.0)
- `/simulation` contains the actual simulation, decoupled from django
- `/cats` is the django app, that contains:
  - Basic models for Simulation Run and Results persistence
  - Management command: `python manage.py run_simulation`
  - Celery task: `run_simulation`

- Redis required as Celery broker

### [v2.0.0](https://github.com/hannaseithe/catSim/releases/tag/v2.0.0):
- the simulation is now accessible through an API, with JWT based authentication:
  - `/api/simulations/`:`GET` -> Get List of Simulations is returned (for normal users only Simulations that they created, and for admin all simulations)
  - `/api/simulations/start/`:`POST` -> Start a simulation (queued with Celery)
  - `/api/simulations/<id>/`:`GET` -> Get Simulation with status and params
  - `/api/simulations/<id>/results/`:`GET` -> Get Simulation results if finished
  - `/api/simulations/<id>/`:`GET` -> Get Simulation error if failed
 
- for authentication:
  -  `/api/token/`:`POST`-> Get Access Token / Login
  -  `/api/token/refresh`:`POST` -> Refresh Token

 #### [v2.1.0](https://github.com/hannaseithe/catSim/releases/tag/v2.0.0):
Added filtering, ordering and pagination to  `/api/simulations/`:`GET` endpoint

Filters:
e.g. `/api/simulations/?status=finished&user=2`
- `status` match: `exact`
- `user` match: `exact`
- `created_at_min` match `>=` (accepts DateTime Iso Format)
- `created_at_max`  match `<=` (accepts DateTime Iso Format)
- `iterations` match: `exact`
- `iterations_min` match `>=`
- `iterations_max`  match `<=`
- `cat_amount` match: `exact`
- `cat_amount_min` match `>=`
- `cat_amount_max`  match `<=`
- `node_amount` match: `exact`
- `node_amount_min` match `>=`
- `node_amount_max`  match `<=`

Order_Fields:
e.g. `/api/simulations/?ordering=iterations`
- `created_at`
- `iterations`
- `cat_amount`
- `node_amount`

Pagination:
e.g. `/api/simulations/?page=2&page_size=20`
- `page_size` defines the size of a page
- `page` defines the page number 
