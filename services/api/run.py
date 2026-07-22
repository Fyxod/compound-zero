"""Console entry point for the Compound Zero API."""

from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run("services.api.main:app", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()

