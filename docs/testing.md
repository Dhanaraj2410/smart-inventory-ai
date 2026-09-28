# Testing and checks

Run commands from the repository root with the project virtual environment
active. The project uses Django's test runner and SQLite by default, so the
test suite does not need a separate database server.

## Full suite

```sh
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Django creates a temporary test database; it does not use the local
`db.sqlite3` for test data.

## Run a focused test

Pass an app label or dotted test module to Django's test runner:

```sh
python manage.py test apps.products
python manage.py test apps.sales
python manage.py test tests.test_api
```

Put tests next to the app they cover (`apps/<app>/tests.py`) or in the
repository-level `tests/` package for integration coverage. Prefer assertions
on persisted outcomes and API response status/data over implementation
details.

## Optional data and services

Most tests use small fixtures created in `setUp` and need no seeded sample
dataset. When investigating model behavior, generate and load sample data as
described in [local development](development.md). Tests that depend on
external services should mock the boundary rather than requiring Redis or a
Hugging Face credential.

If checks fail, retain the first failing test and traceback when reporting
the issue; warnings about local static files or serialized ML artifacts may
be environment-specific and should be reported separately from test failures.
