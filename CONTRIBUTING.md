# Contributing

Thanks for helping improve Smart Inventory AI. Keep changes focused and
include tests or documentation for behavior that changes.

## Before you start

- Use Python 3.12, the version documented for this project.
- Read [the development setup](docs/development.md) and [the test guide](docs/testing.md).
- Check the existing issues and pull requests before starting a large change.

## Making a change

1. Create a branch from the current default branch.
2. Make one focused change at a time and follow the existing Django app structure.
3. Put business logic in the relevant app's `services.py` or the shared
   `services/` package rather than adding it to a view.
4. Add or update tests alongside the affected app.
5. Run `python manage.py check` and `python manage.py test` before opening a
   pull request.
6. Update the README or a page under `docs/` if commands, configuration, or
   user-visible behavior changed.

## Database changes

Create migrations with `python manage.py makemigrations`, review the generated
files, and include them in the same change as the model update. Check for
uncommitted model changes with:

```console
python manage.py makemigrations --check --dry-run
```

Do not commit local databases, uploaded media, generated sample CSVs, model
artifacts, or `.env` files.

## Pull requests

Describe the reason for the change, summarize its behavior, and include the
commands used to test it. Call out any migration, configuration, or deployment
steps that reviewers need to know about.
