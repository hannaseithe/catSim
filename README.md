# Cat Simulation Project

I simulate the relationships of cats developing over time. Currently this serves mainly the purpose of practicing headless Django with a fun little simulation behind it

### v1:
- `/simulation` contains the actual simulation, decoupled from django
- `/cats` is the django app, that contains:
  - Basic models for Simulation Run and Results persistence
  - Management command: `python manage.py run_simulation`
  - Celery task: `run_simulation`

- Redis required as Celery broker 
