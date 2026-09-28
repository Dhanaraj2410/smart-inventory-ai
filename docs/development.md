# Local development

The default settings use SQLite and do not require MySQL, Redis, or a
Hugging Face API key. Use Python 3.12, as listed in the project tech stack.

## Windows PowerShell

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py runserver
```

If PowerShell blocks activation, either adjust the execution policy for the
current user according to your organization's guidance or invoke the
environment's interpreter directly as `.venv\Scripts\python.exe`.

## macOS and Linux

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

Keep `DB_ENGINE=sqlite` for this quick start. The application is then
available at <http://127.0.0.1:8000/>. Create an administrator with
`python manage.py createsuperuser` if you need access to Django admin.

## Load sample inventory

Sample files are generated locally and are ignored by Git:

```sh
python ml/data/generate_sample_data.py
python manage.py seed_data
```

`seed_data` replaces sales history for the sample product SKUs, so use it
only with a disposable development database. Add `--skip-sales` to load the
sample products without importing the sales history.

See [configuration](configuration.md) for environment variables and
[containers](containers.md) for the MySQL/Redis setup.
