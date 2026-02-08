from __future__ import annotations

from typing import List, Tuple

import typer
from dotenv import load_dotenv

from pipeline.clean import clean
from pipeline.embed import embed
from pipeline.fingerprint import fingerprint
from pipeline.geocode import geocode
from pipeline.upload import upload

app = typer.Typer(add_completion=False)


@app.command()
def run(from_step: str = typer.Option("clean", "--from")) -> None:
    """Run the full pipeline starting from a step."""
    load_dotenv()
    steps: List[Tuple[str, callable]] = [
        ("clean", clean),
        ("geocode", geocode),
        ("fingerprint", fingerprint),
        ("embed", embed),
        ("upload", upload),
    ]

    step_names = [name for name, _ in steps]
    if from_step not in step_names:
        raise typer.BadParameter(f"Unknown step: {from_step}")

    start_index = step_names.index(from_step)
    for _, step_fn in steps[start_index:]:
        step_fn()


@app.command(name="clean")
def clean_step() -> None:
    load_dotenv()
    clean()


@app.command(name="geocode")
def geocode_step() -> None:
    load_dotenv()
    geocode()


@app.command(name="fingerprint")
def fingerprint_step() -> None:
    load_dotenv()
    fingerprint()


@app.command(name="embed")
def embed_step() -> None:
    load_dotenv()
    embed()


@app.command(name="upload")
def upload_step() -> None:
    load_dotenv()
    upload()


if __name__ == "__main__":
    app()
