# zapiski-ai-auth

Authentication for the zapiski AI service

## Development

### Locally

In this case, postgresql is deployed through docker-compose, and poetry packages are installed locally:

- In repo `zapiski-ai-dev-env`, start docker compose.
- To setup python packages and start the server (prerequisite: `poetry`):
  - `poetry install`
  - `cp .example.env .env`
  - `poetry run uvicorn src.main:app --reload`

## Provided requests

Are located in `zapiski-ai-dev-env` Postman collection.

## Additional comments

Tjaz: By default, I was running this on port 8000. If you're running multiple API servers (e.g., this and auth) at the same time
during local development, they have to be exposed over different ports. I just use various random defaults here.
