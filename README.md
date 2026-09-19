# Advoxy

Advoxy is a Django REST and Next.js marketplace for on-demand hair and nail services.

## Local Windows setup

Use one environment for the backend: the repository root `.venv`. The older `backend\venv` is not part of the supported workflow.

```powershell
cd C:\Users\10adn\Downloads\advoxy
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt

$env:USE_SQLITE="1"
python backend\manage.py migrate
python backend\manage.py seed_demo
python backend\manage.py check
python backend\manage.py test accounts bookings reviews
```

Start the API:

```powershell
$env:USE_SQLITE="1"
python backend\manage.py runserver 8000
```

Start the customer web app in a second terminal:

```powershell
cd C:\Users\10adn\Downloads\advoxy\frontend
npm install
npm run dev
```

The web app runs at `http://localhost:3000` and the API at `http://127.0.0.1:8000`.

## PostgreSQL and workers

Production uses PostgreSQL. Set `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, and `POSTGRES_PORT`, leave `USE_SQLITE` unset, and run migrations with the same commands above.

With Redis running, start the asynchronous processes from the repository root:

```powershell
.\.venv\Scripts\Activate.ps1
celery -A advoxy_backend worker -l INFO --workdir backend
celery -A advoxy_backend beat -l INFO --workdir backend
```

## Configuration

Copy the environment example and provide production credentials before enabling external integrations:

```powershell
Copy-Item backend\.env.example backend\.env
```

External integrations fail clearly when credentials are absent; the application does not report fake payment, notification, verification, location, or upload success.# Advoxy_ODS
