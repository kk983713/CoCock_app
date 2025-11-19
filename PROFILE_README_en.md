<!--
  GitHub profile README (English) - copy this into https://github.com/kk983713/kk983713/README.md
-->

# CoCock

*A prototype for quickly recording and searching photo-backed recipes.*

- Frontend: Streamlit
- Token proxy: FastAPI-based short-ID service (token_store)
- Persistence: SQLite (local development)

Highlights:

- Supports anonymous recipe submission while keeping edit tokens server-side: only a short_id is shared with the client to reduce token leakage risk.
- Headless E2E tests (Playwright) validate flows and save screenshots/HTML snapshots as artifacts.

Supplementary materials (PDF) and demo screenshots are included in the repo. Links below use the username `kk983713`:

- Repository: https://github.com/kk983713/CoCock_app
- Supplementary PDF: https://github.com/kk983713/CoCock_app/raw/main/docs/cocock_supplementary.pdf

---

Short summary (one-liner):

CoCock — a photo-first recipe logging and search prototype that uses a short-ID token proxy to safely connect anonymous submissions to authenticated owners.
