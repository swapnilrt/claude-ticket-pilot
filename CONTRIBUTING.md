# Contributing to Claude Ticket Pilot

Thank you for your interest in contributing! This document explains how to get involved.

## How to Contribute

- **Bug reports** — Open a GitHub issue with a clear description, steps to reproduce, and the relevant log output.
- **Feature requests** — Open a GitHub issue describing the use case and proposed behaviour before writing code.
- **Code changes** — Fork the repository, make your changes on a feature branch, and open a pull request (see below).

## Development Setup

1. Clone the repository and create a virtual environment:

```bash
git clone https://github.com/yourorg/claude-ticket-pilot.git
cd claude-ticket-pilot
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy the example environment file and fill in your tracker credentials:

```bash
cp .env.example .env
# edit .env with your TRACKER_* values
```

## Running Tests

```bash
python -m pytest test_skill.py -v
```

All tests must pass before submitting a pull request.

## Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) for Python code.
- Use descriptive variable and function names.
- Keep functions focused and small — prefer many small functions over a few large ones.
- Add docstrings to public functions and classes.
- Do not commit secrets, credentials, or personal data.

## Submitting Pull Requests

1. Create a feature branch from `main`:

```bash
git checkout -b my-feature
```

2. Make your changes and commit with a clear message:

```bash
git commit -m "Add support for X"
```

3. Push your branch and open a pull request against `main`:

```bash
git push origin my-feature
```

4. In the pull request description, explain *what* changed and *why*. Link any related issues.
5. A maintainer will review your PR. Please respond to feedback promptly and update the branch as needed.
6. Once approved, a maintainer will merge your PR.

## Questions

If you are unsure about anything, open a GitHub issue and ask — we are happy to help.
