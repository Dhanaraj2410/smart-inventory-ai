# Troubleshooting

## Django cannot be imported

Activate the project virtual environment and install the project requirements:

```sh
python -m pip install -r requirements.txt
python -m django --version
```

Use Python 3.12, as described in [local development](development.md).

## Database connection errors

The default `DB_ENGINE=sqlite` does not need a database server. If using MySQL,
verify `DB_ENGINE`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and
`DB_PASSWORD`; then run `python manage.py migrate`. Inside Compose, the
database host is `db`, not `localhost`.

## Redis or Celery errors

The web application can run locally without a Celery worker. Background jobs
need a reachable Redis server and a `REDIS_URL` that points to it. In Compose,
the service hostname is `redis`; outside Compose, use the host and port where
Redis is listening.

## Empty dashboard or prediction pages

Apply migrations, create an administrator, and load sample inventory as
described in [local development](development.md). The sample CSV files are
generated on demand and are not included in a fresh checkout.

## Hugging Face requests do not run

Without `HUGGINGFACE_API_KEY`, AI answers use the local grounded fallback. To
use the hosted model, configure the key and confirm that the selected model is
available to the account. Numeric inventory predictions do not depend on the
language model.

## Static-file warning during local tests

Django may warn that the `staticfiles` collection directory is missing before
`collectstatic` has been run. This is separate from a failed test assertion.
For a deployment-style static-file check, run `python manage.py collectstatic
--noinput` and inspect the command output.
