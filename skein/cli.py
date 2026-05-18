"""Skein CLI."""
from __future__ import annotations

import os
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()


def _env(key: str, default: str | None = None) -> str:
    v = os.environ.get(key, default)
    if v is None:
        console.print(f"[red]missing env var {key}[/]")
        raise typer.Exit(1)
    return v


def _predicates() -> list[str] | None:
    raw = os.environ.get("SKEIN_PREDICATES", "").strip()
    if not raw:
        return None
    return [p.strip() for p in raw.split(",") if p.strip()]


@app.command()
def build(
    top_k: int = typer.Option(6, "--top-k", envvar="SKEIN_EDGE_TOP_K"),
    min_sim: float = typer.Option(0.55, "--min-sim", envvar="SKEIN_EDGE_MIN_SIM"),
    window: int = typer.Option(120, "--window", envvar="SKEIN_PREDICATE_WINDOW"),
):
    """Build the Skein knowledge graph from scratch."""
    from skein.core import build_skein
    db = _env("SKEIN_DB_URL")
    stats = build_skein(
        db,
        ollama_url=_env("SKEIN_OLLAMA_URL"),
        embed_model=_env("SKEIN_EMBED_MODEL"),
        chat_model=_env("SKEIN_CHAT_MODEL"),
        predicates=_predicates(),
        top_k=top_k, min_sim=min_sim, window=window,
        log=console.print,
    )
    console.print(f"[green]done[/] · {stats}")


@app.command()
def stats():
    """Show counts."""
    import psycopg
    with psycopg.connect(_env("SKEIN_DB_URL")) as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM skein_entities"); ne = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM skein_relations"); nr = cur.fetchone()[0]
        cur.execute("SELECT kind, COUNT(*) FROM skein_entities GROUP BY kind ORDER BY 2 DESC LIMIT 10")
        kinds = cur.fetchall()
        cur.execute("SELECT predicate, COUNT(*) FROM skein_relations GROUP BY predicate ORDER BY 2 DESC LIMIT 10")
        preds = cur.fetchall()
        cur.execute("SELECT name, mentions FROM skein_entities ORDER BY mentions DESC LIMIT 10")
        top = cur.fetchall()
    console.print(f"[bold]entities[/] {ne}  [bold]relations[/] {nr}")
    if kinds:
        t = Table(title="entity kinds"); t.add_column("kind"); t.add_column("n", justify="right")
        for k, n in kinds: t.add_row(str(k), str(n))
        console.print(t)
    if preds:
        t = Table(title="top predicates"); t.add_column("predicate"); t.add_column("n", justify="right")
        for p, n in preds: t.add_row(str(p), str(n))
        console.print(t)
    if top:
        t = Table(title="most-mentioned entities"); t.add_column("name"); t.add_column("mentions", justify="right")
        for n, m in top: t.add_row(str(n), str(m))
        console.print(t)


@app.command()
def neighbors(
    name: str = typer.Argument(...),
    limit: int = typer.Option(20, "--limit"),
):
    """Show one entity's neighbors and predicates."""
    from skein.core import neighbors_of
    r = neighbors_of(_env("SKEIN_DB_URL"), name, limit=limit)
    if not r["found"]:
        console.print(f"[yellow]no entity matching '{name}'[/]"); raise typer.Exit(1)
    console.print(f"[bold]{r['name']}[/] [dim]({r['kind']}, {r['mentions']} mentions)[/]")
    t = Table()
    for col in ("dir", "predicate", "other", "kind", "sim", "evidence"):
        t.add_column(col)
    for e in r["edges"]:
        t.add_row(e["direction"], e["predicate"], e["other"], str(e["kind"]),
                  f"{e['sim']:.3f}", ", ".join(str(c) for c in e["evidence"][:3]))
    console.print(t)


if __name__ == "__main__":
    app()
