# Docker Compose

The Compose stack starts MySQL, Redis, the Django web service, a Celery worker,
and Celery beat. It is intended as a production-shaped local environment; the
quickest development path is SQLite as described in [local development](development.md).

## Start the stack

1. Install Docker Desktop or Docker Engine with the Compose plugin.
2. Copy `.env.example` to `.env` in the repository root.
3. Set a non-empty `DB_PASSWORD` in `.env`.
4. Start the services:

   ```sh
   docker compose up --build
   ```

The web container applies migrations and collects static files before starting
Gunicorn. Open <http://127.0.0.1:8000/> once the web service is ready. Compose
overrides `DB_HOST` and `REDIS_URL` for service-to-service networking.

## Useful commands

```sh
docker compose ps
docker compose logs -f web
docker compose logs -f celery_worker
docker compose down
```

The database, static files, and uploaded media use named volumes. `docker
compose down` keeps those volumes. Removing volumes with `docker compose down
-v` permanently deletes the persisted local database and files; only do so
when you intend to reset the development stack.

The Compose file publishes MySQL and Redis ports on the host for local access.
Do not expose those ports to untrusted networks in a deployed environment.
