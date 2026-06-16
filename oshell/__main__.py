"""Allow ``python -m oshell`` to launch the CLI."""

from .cli import app

if __name__ == "__main__":
    app()
