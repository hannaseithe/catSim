# Cat Simulation Project

Simulate the relationships of cats developing over time. Currently this serves mainly the purpose of practicing headless Django and Django REST Framework with a fun little simulation behind it


#### [v4.0.0](https://github.com/hannaseithe/catSim/releases/tag/v4.0.0):
- **Dockerization**: the whole app, as well as celery, redis, postgres, nginx have been dockerized and can now be deployed with docker compose on a server
- **Internal Event Logging**: simulation runs now emit events that are persisted to the DB. There are three types:
  - `PROGRESS`: time-interval based emissions of the simulation runs progress
  - `STATE_TRANSITION`: when a run changes state, e.g. RUNNING > FINISHED
  - `QUEUE`: when a run is queued for Start or Resume
- **Websocket Connection**: a authenticated websocket connection allows users to subscribe to the event emission for a specific run
  - the adress is: `ws://<url>/events/<run_id>/`
  - authentication is first message based, the message must follow the format: `{"access": "<your-access-token>"}`
- **New Monitoring Endpoints**:
  - `GET /api/v1/simulations/health/` - get stats about the API's health
  - `GET /api/v1/simulations/queue-status/` - get data about the current queue's status
- **Caching Results Endpoint**: as the most data intensive endpoint with immutable data, the results will be cached indefinitely

#### [v3.0.0](https://github.com/hannaseithe/catSim/releases/tag/v3.0.0):
- **Checkpointing**: simulation state is saved to the database every N iterations (configurable via `SIMULATION_CHECKPOINT_INTERVAL`), enabling recovery without starting from scratch
- **Pause/Resume**: simulations can be paused mid-run and resumed from the last checkpoint
  - `POST /api/v1/simulations/<id>/pause/` — requests a pause; processed at the next tick
  - `POST /api/v1/simulations/<id>/resume/` — re-queues the simulation from its last checkpoint; also works for canceled and failed runs
- **Crash recovery**: on Celery worker restart, any simulation stuck in a running state is automatically re-queued from its last checkpoint
- **Idempotency**: resume endpoint is protected against duplicate queuing with row-level locking
- **ADR documentation**: architectural decisions are now documented in `docs/adr/`

#### [v2.2.0](https://github.com/hannaseithe/catSim/releases/tag/v2.2.0):
- Added Versioning to API: Version 1 of API to be found under `/api/v1/` and old API has been deprecated
- Idempotent `/api/simulations/start`endpoint by adding `uuid` query parameter 
- Added new `cancel` and `delete` endpoints
 - `/api/simulations/<id>/cance/l`:`POST`
 - `/api/simulations/<id>/delete/`:`DELETE`
- Added **OpenAPI schema definition** and swaggerUI documentation
- Added **Schemathesis tests** of the v1 API based on the OpenAPI definition
- Created Postman collection based on OpenAPI schema: https://www.postman.com/hanna-seithe/workspace/catsim/collection/1998245-4f7997af-b044-4843-910f-4a0574acdef7?action=share&source=copy-link&creator=1998245

 #### [v2.1.0](https://github.com/hannaseithe/catSim/releases/tag/v2.1.0):
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

  ### [v1.0.0](https://github.com/hannaseithe/catSim/releases/tag/v1.0.0)
- `/simulation` contains the actual simulation, decoupled from django
- `/cats` is the django app, that contains:
  - Basic models for Simulation Run and Results persistence
  - Management command: `python manage.py run_simulation`
  - Celery task: `run_simulation`

- Redis required as Celery broker
