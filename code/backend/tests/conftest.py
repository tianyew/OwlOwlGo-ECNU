"""Optional real PostgreSQL integration test switch."""


def pytest_addoption(parser):
    parser.addoption(
        "--postgres", action="store_true",
        help="Run PostgreSQL tests using DATABASE_URL from backend/.env (isolated schemas)",
    )

