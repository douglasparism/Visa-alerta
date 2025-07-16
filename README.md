# visa-alerta

**visa-alerta** is a Dockerized Python tool that watches the U.S. visa appointment page and sends you an email (via SendGrid) when a new appointment slot appears.

## Features
- Headless browser login (Playwright)
- Configurable polling interval
- JSON-based state tracking
- Email alerts via SendGrid
- Docker-ready
- GitHub Actions CI (flake8 + Docker build)

## Getting Started

### Prerequisites
- Docker
- [Mailgun](https://www.mailgun.com/) account & API key

### Local Setup

1. Copy and edit `.env.example`:
   ```bash
   cp .env.example .env
   ```

2. (Optional) Create and activate a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install --no-cache-dir -r requirements.txt
   ```

4. Build and run:
   ```bash
   docker build -t visa-alerta .
   docker run --env-file .env visa-alerta
   ```

## Configuration

| Variable           | Description                 | Default |
| ------------------ | --------------------------- | ------- |
| VISA\_EMAIL        | Your visa site email        | —       |
| VISA\_PASS         | Your visa site password     | —       |
| SENDGRID\_API\_KEY | Your SendGrid API key       | —       |
| EMAIL\_FROM        | From address for alerts     | —       |
| EMAIL\_TO          | Recipient address           | —       |
| POLL\_INTERVAL     | Polling interval in seconds | 600     |

## CI / GitHub Actions

See `.github/workflows/ci.yml` for linting and Docker build checks.

## License

This project is licensed under the MIT License.