# zapiski-ai-auth

Authentication for the zapiski AI service

For API endpoints documentation run the service and look at: http://127.0.0.1:8001/docs

## Development

### Locally

In this case, postgresql is deployed through docker-compose, and poetry packages are installed locally:

- In repo `zapiski-ai-dev-env`, start docker compose.
- To setup python packages and start the server (prerequisite: `poetry`):
  - `poetry install`
  - `cp .example.env .env`
  - `poetry run uvicorn src.main:app --reload --port 8001`

## Provided requests

Are located in `zapiski-ai-dev-env` Postman collection.

## Accessing API Documentation

The API documentation is available via Swagger UI, which provides detailed information about all endpoints, including request/response formats, parameters, and example responses.

### 1. Access Locally
To view the documentation when running the service locally:
1. Start the service.
2. Open your browser and navigate to: [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs).

### 2. Access When Deployed on Kubernetes
When the service is deployed on Kubernetes:
1. Ensure the service is exposed through an **Ingress** or **LoadBalancer**.
2. Obtain the external URL of the service. For example:
   - If the service is exposed at `http://api.example.com`, open your browser and navigate to:
     ```
     http://api.example.com/docs
     ```
     
## Additional comments

Tjaz: By default, I was running this on port 8001. If you're running multiple API servers (e.g., this and auth) at the same time
during local development, they have to be exposed over different ports. I just use various random defaults here.
