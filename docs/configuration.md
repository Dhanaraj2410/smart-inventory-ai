# Configuration reference

Copy `.env.example` to `.env` for local overrides. Settings are read by
`python-decouple`; unset values use the defaults below. Do not commit `.env`
or put production credentials in source control.

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | `dev-only-insecure-key` | Django signing key. Set a unique, private value outside local development. |
| `DEBUG` | `True` | Enables Django debug behavior. Set to `False` in production. |
| `ALLOWED_HOSTS` | `127.0.0.1,localhost` | Comma-separated hostnames accepted by Django. |
| `DB_ENGINE` | `sqlite` | Select `sqlite` or `mysql`. |
| `DB_NAME` | `smart_inventory` | MySQL database name. |
| `DB_USER` | `root` | MySQL username. |
| `DB_PASSWORD` | empty | MySQL password. |
| `DB_HOST` | `localhost` | MySQL host; Compose overrides it to `db`. |
| `DB_PORT` | `3306` | MySQL port. |
| `REDIS_URL` | `redis://localhost:6379/0` | Celery broker and result backend. |
| `HUGGINGFACE_API_KEY` | empty | Optional credential; the assistant uses its grounded fallback when absent. |
| `HUGGINGFACE_MODEL` | `google/flan-t5-base` | Text-generation model identifier. |
| `HUGGINGFACE_CLASSIFIER_MODEL` | `facebook/bart-large-mnli` | Classification model identifier. |
| `EMAIL_HOST` | empty | SMTP host. Without it, email uses Django's console backend. |
| `EMAIL_PORT` | `587` | SMTP port. TLS is enabled in settings. |
| `EMAIL_HOST_USER` | empty | SMTP username. |
| `EMAIL_HOST_PASSWORD` | empty | SMTP password. |
| `DEFAULT_FROM_EMAIL` | `alerts@smart-inventory.local` | Sender address for application email. |

When `DB_ENGINE=mysql`, configure the `DB_*` values and make the database
reachable before starting Django. For production, explicitly configure
`SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`, database credentials, and
`REDIS_URL`. Review Django's deployment checklist for additional
environment-specific hardening.

Business defaults such as supplier lead time and safety-stock days are
currently defined in `config/settings.py`, not in `.env`.
