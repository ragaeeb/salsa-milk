# Salsa Milk Workspace Guide

- Use `rg` for code search instead of recursive `grep` or `find`.
- Prefer `pytest` for running the automated test suite; invoke `pytest --maxfail=1 --disable-warnings` during development.
- The project exposes both a CLI (`salsa-milk.py`), a Flask app (`webapp.py`), and a Streamlit interface (`streamlit_app.py`).  Keep shared logic inside `salsa_milk_core.py`.
- Tests live under the `tests/` directory.  Add new tests alongside the modules they exercise.
- When editing templates, keep them under `templates/` and reuse shared styles from `templates/index.html` where possible.
- Document new deployment targets in the README when functionality changes affect end users.
