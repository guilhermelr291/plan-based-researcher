"""Extract figures, tables, and display equations from one arXiv HTML paper
(spike, not wired in).

Local extras (not project dependencies):

    pip install beautifulsoup4 lxml markdownify tiktoken

tiktoken is already transitive via the OpenAI stack; still listed so a
minimal environment can run this script. Fetch uses the project's httpx.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urljoin, urlparse

import httpx

from plan_based_researcher.policy import Policy

_ROOT = Path(__file__).resolve().parents[1]
_USER_AGENT = (
    "plan-based-researcher-html-units/0.1 "
    "(local research spike; not a crawler; https://arxiv.org/help/robots)"
)
_TIMEOUT = httpx.Timeout(30.0)
_ARTICLE_ROOT = (
    "section.ltx_section, div.ltx_page_content, article.ltx_document, "
    "div.ltx_document, div.ltx_page_main"
)
_ASSET_TAGS = ("img", "object", "embed", "source")
_UNSAFE_ID = re.compile(r"[^\w.\-]+", re.UNICODE)
_DISPLAYSTYLE = re.compile(r"\\displaystyle\s*")
_EQUATION_CLASSES = frozenset({"ltx_equation", "ltx_equationgroup"})


def main() -> None:
    args = _parse_args()
    _require_extras()

    arxiv_id = args.arxiv_id.strip()
    version = args.version.strip().lstrip("vV")
    html_url = f"https://arxiv.org/html/{arxiv_id}v{version}"
    out = args.out or (_ROOT / "_tmp_arxiv_html" / f"{arxiv_id}v{version}")
    if not out.is_absolute():
        out = Path.cwd() / out

    html_bytes = _fetch(html_url)
    out.mkdir(parents=True, exist_ok=True)
    (out / "paper.html").write_bytes(html_bytes)

    soup = _parse_html(html_bytes)
    if soup.select_one(_ARTICLE_ROOT) is None:
        print(
            f"error: no article root (expected {_ARTICLE_ROOT}) at {html_url}",
            file=sys.stderr,
        )
        sys.exit(1)

    units_dir = out / "units"
    if units_dir.exists():
        shutil.rmtree(units_dir)
    units_dir.mkdir()

    with httpx.Client(
        headers={"User-Agent": _USER_AGENT},
        timeout=_TIMEOUT,
        follow_redirects=True,
    ) as client:
        units = _extract_units(soup, client=client, html_url=html_url, units_dir=units_dir)

    convert_root = (
        soup.select_one("article.ltx_document")
        or soup.select_one("div.ltx_page_content")
        or soup.body
        or soup
    )
    _rewrite_inline_math(convert_root)
    prose = _html_to_markdown(convert_root)
    (out / "prose.md").write_text(prose, encoding="utf-8")
    (out / "sections.txt").write_text(_heading_outline(soup), encoding="utf-8")

    encoder = _token_encoder()
    chunk_size = Policy.chunk_size
    manifest: list[dict[str, Any]] = []
    for unit in units:
        token_src = unit["tex"] if unit["kind"] == "equation" else unit["html"]
        tokens = _count_tokens(encoder, token_src)
        row: dict[str, Any] = {
            "kind": unit["kind"],
            "html_id": unit["html_id"],
            "caption": unit["caption"],
            "html_path": unit["html_path"],
        }
        if unit["kind"] == "equation":
            row["tex_path"] = unit["tex_path"]
            row["tex"] = unit["tex"]
        row["assets"] = unit["assets"]
        row["tokens"] = tokens
        row["fits_512"] = tokens <= chunk_size
        manifest.append(row)
        del unit["html"]

    (units_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    _print_report(soup, manifest, encoder, chunk_size)
    print(f"Wrote {out}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch arXiv HTML and split out innermost figures, tables, "
            "and display equations."
        )
    )
    parser.add_argument("arxiv_id", help="arXiv id (never infers latest by itself)")
    parser.add_argument("version", help="Version digit(s), e.g. 1 (required, never implicit)")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output directory (default: _tmp_arxiv_html/{id}v{ver} at repo root)",
    )
    return parser.parse_args()


def _require_extras() -> None:
    missing: list[str] = []
    try:
        import bs4  # noqa: F401
    except ImportError:
        missing.append("beautifulsoup4")
    try:
        import lxml  # noqa: F401
    except ImportError:
        missing.append("lxml")
    try:
        import markdownify  # noqa: F401
    except ImportError:
        missing.append("markdownify")
    try:
        import tiktoken  # noqa: F401
    except ImportError:
        missing.append("tiktoken")
    if missing:
        print(
            "Missing local extras: "
            + ", ".join(missing)
            + "\nInstall with: pip install beautifulsoup4 lxml markdownify tiktoken",
            file=sys.stderr,
        )
        sys.exit(1)


def _fetch(url: str) -> bytes:
    try:
        response = httpx.get(
            url,
            headers={"User-Agent": _USER_AGENT},
            timeout=_TIMEOUT,
            follow_redirects=True,
        )
    except httpx.HTTPError as exc:
        print(f"error: GET {url} failed: {exc}", file=sys.stderr)
        sys.exit(1)
    if response.status_code != 200:
        print(f"error: GET {url} returned {response.status_code}", file=sys.stderr)
        sys.exit(1)
    if not response.content:
        print(f"error: empty body from {url}", file=sys.stderr)
        sys.exit(1)
    return response.content


def _parse_html(html_bytes: bytes) -> Any:
    from bs4 import BeautifulSoup, FeatureNotFound

    try:
        return BeautifulSoup(html_bytes, "lxml")
    except FeatureNotFound:
        print(
            "error: lxml parser is not available. Install with: pip install lxml",
            file=sys.stderr,
        )
        sys.exit(1)


def _extract_units(
    soup: Any,
    *,
    client: httpx.Client,
    html_url: str,
    units_dir: Path,
) -> list[dict[str, Any]]:
    from bs4 import Tag

    nodes = [
        node
        for node in soup.find_all(["table", "figure"])
        if isinstance(node, Tag)
    ]
    ranked = sorted(
        enumerate(nodes),
        key=lambda item: (-_dom_depth(item[1]), item[0]),
    )

    used_stems: set[str] = set()
    generated = 0
    units: list[dict[str, Any]] = []
    for _, node in ranked:
        kind = _unit_kind(node)
        raw_id = (node.get("id") or "").strip()
        if raw_id:
            html_id = raw_id
        else:
            generated += 1
            html_id = f"unit-{generated:04d}"
        stem = _unique_stem(f"{kind}-{_safe_id(html_id)}", used_stems)
        caption = _unit_caption(node, kind)
        if kind == "equation":
            assets: list[str] = []
            tex = _equation_tex(node)
            rel_tex = f"units/{stem}.tex"
            tex_body = tex if tex.endswith("\n") else tex + "\n"
            (units_dir / f"{stem}.tex").write_text(tex_body, encoding="utf-8")
        else:
            assets = _download_assets(
                node,
                client=client,
                html_url=html_url,
                units_dir=units_dir,
                stem=stem,
            )
            tex = ""
            rel_tex = ""
        snapshot = str(node)
        rel_html = f"units/{stem}.html"
        (units_dir / f"{stem}.html").write_text(snapshot, encoding="utf-8")
        placeholder = soup.new_tag("p")
        placeholder.string = f"[{kind.upper()}:{html_id}]"
        node.replace_with(placeholder)
        unit: dict[str, Any] = {
            "kind": kind,
            "html_id": html_id,
            "caption": caption,
            "html_path": rel_html,
            "assets": assets,
            "html": snapshot,
        }
        if kind == "equation":
            unit["tex_path"] = rel_tex
            unit["tex"] = tex
        units.append(unit)
    return units


def _unit_kind(node: Any) -> str:
    if node.name != "table":
        return "figure"
    classes = set(node.get("class") or [])
    if classes & _EQUATION_CLASSES:
        return "equation"
    if "ltx_eqn_table" in classes and "ltx_tabular" not in classes:
        return "equation"
    return "table"


def _unit_caption(node: Any, kind: str) -> str:
    if kind == "equation":
        tag = node.find(class_="ltx_tag_equation") if hasattr(node, "find") else None
        if tag is None:
            return ""
        return tag.get_text(" ", strip=True)
    return _caption_text(node)


def _caption_text(root: Any) -> str:
    from bs4 import Tag

    node = root.find("figcaption") if hasattr(root, "find") else None
    if node is None and hasattr(root, "find"):
        node = root.find(class_="ltx_caption")
    if not isinstance(node, Tag):
        return ""
    return node.get_text(" ", strip=True)


def _math_tex(node: Any) -> str:
    from bs4 import Tag

    if not isinstance(node, Tag):
        return ""
    annotation = node.find("annotation", attrs={"encoding": "application/x-tex"})
    raw = annotation.get_text() if annotation is not None else ""
    if not raw.strip() and node.name == "math":
        raw = node.get("alttext") or ""
    return _DISPLAYSTYLE.sub("", raw).strip()


def _equation_tex(node: Any) -> str:
    parts: list[str] = []
    maths = node.find_all("math") if hasattr(node, "find_all") else []
    for math in maths:
        tex = _math_tex(math)
        if tex:
            parts.append(tex)
    if not parts:
        tex = _math_tex(node)
        if tex:
            parts.append(tex)
    if not parts:
        return ""
    return "$$\n" + "\n".join(parts) + "\n$$"


def _rewrite_inline_math(root: Any) -> None:
    from bs4 import NavigableString, Tag

    if not hasattr(root, "find_all"):
        return
    for math in list(root.find_all("math", class_="ltx_Math")):
        if not isinstance(math, Tag):
            continue
        tex = _math_tex(math)
        math.replace_with(NavigableString(f"${tex}$" if tex else ""))


def _html_to_markdown(root: Any) -> str:
    from markdownify import MarkdownConverter

    class ArxivHtmlConverter(MarkdownConverter):
        def convert_cite(self, el, text, parent_tags):
            labels = [
                a.get_text(" ", strip=True)
                for a in el.find_all("a")
                if a.get_text(" ", strip=True)
            ]
            if labels:
                return "[" + ", ".join(labels) + "]"
            return (text or "").strip()

    return ArxivHtmlConverter(
        heading_style="ATX",
        wrap=False,
        bs4_options="lxml",
        strip=["script", "style", "nav"],
        escape_underscores=False,
    ).convert_soup(root)


def _dom_depth(tag: Any) -> int:
    depth = 0
    current = getattr(tag, "parent", None)
    while current is not None:
        depth += 1
        current = getattr(current, "parent", None)
    return depth


def _safe_id(html_id: str) -> str:
    cleaned = _UNSAFE_ID.sub("_", html_id).strip("._") or "unnamed"
    return cleaned[:120]


def _unique_stem(stem: str, used: set[str]) -> str:
    candidate = stem
    n = 2
    while candidate in used:
        candidate = f"{stem}-{n}"
        n += 1
    used.add(candidate)
    return candidate


def _download_assets(
    node: Any,
    *,
    client: httpx.Client,
    html_url: str,
    units_dir: Path,
    stem: str,
) -> list[str]:
    from bs4 import Tag

    # Resolve against the document URL (no extra slash). arXiv HTML uses
    # paths like "2310.17513v1/figure1.svg" which only work if the last
    # path segment is the paper id, not a directory.
    base = html_url
    saved: list[str] = []
    url_to_file: dict[str, str] = {}
    n = 0
    for el in node.find_all(_ASSET_TAGS):
        if not isinstance(el, Tag):
            continue
        for attr in ("src", "data"):
            raw = (el.get(attr) or "").strip()
            if not raw:
                continue
            if urlparse(raw).scheme in {"data", "javascript", "about"}:
                continue
            abs_url = urljoin(base, raw)
            if abs_url in url_to_file:
                el[attr] = url_to_file[abs_url]
                continue
            n += 1
            filename = _asset_filename(abs_url, stem, n)
            dest = units_dir / filename
            if dest.exists():
                filename = f"{stem}__{n}_{filename}"
                dest = units_dir / filename
            if not _get_asset(client, abs_url, dest):
                continue
            url_to_file[abs_url] = filename
            el[attr] = filename
            saved.append(f"units/{filename}")
    return saved


def _asset_filename(abs_url: str, stem: str, index: int) -> str:
    path = unquote(urlparse(abs_url).path)
    name = Path(path).name or f"asset-{index}"
    name = _UNSAFE_ID.sub("_", name).strip("._") or f"asset-{index}"
    return f"{stem}__{name}"


def _get_asset(client: httpx.Client, url: str, dest: Path) -> bool:
    try:
        response = client.get(url)
    except httpx.HTTPError as exc:
        print(f"warning: asset download failed {url}: {exc}", file=sys.stderr)
        return False
    if response.status_code != 200 or not response.content:
        print(
            f"warning: asset {url} returned {response.status_code}, skipping",
            file=sys.stderr,
        )
        return False
    dest.write_bytes(response.content)
    return True


def _heading_outline(soup: Any) -> str:
    lines: list[str] = []
    for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        level = int(heading.name[1])
        text = heading.get_text(" ", strip=True)
        if text:
            lines.append(f"{'#' * level} {text}")
    return "\n".join(lines) + ("\n" if lines else "")


def _token_encoder() -> Any:
    import tiktoken

    return tiktoken.get_encoding(Policy.chunk_encoding)


def _count_tokens(encoder: Any, text: str) -> int:
    return len(encoder.encode(text, disallowed_special=()))


def _section_chunks(soup: Any) -> list[tuple[str, str]]:
    from bs4 import Tag

    chunks: list[tuple[str, str]] = []
    seen: set[int] = set()
    for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        if not isinstance(heading, Tag):
            continue
        title = heading.get_text(" ", strip=True)
        if not title:
            continue
        section = heading.find_parent("section")
        if (
            isinstance(section, Tag)
            and id(section) not in seen
            and heading is section.find(["h1", "h2", "h3", "h4", "h5", "h6"])
        ):
            seen.add(id(section))
            parts: list[str] = []
            for child in section.children:
                if isinstance(child, Tag) and child.name == "section":
                    continue
                if isinstance(child, Tag):
                    text = child.get_text(" ", strip=True)
                else:
                    text = str(child).strip()
                if text:
                    parts.append(text)
            body = "\n".join(parts)
            label = section.get("id") or title
            chunks.append((str(label), body))
        else:
            chunks.append((title, title))
    return chunks


def _print_report(
    soup: Any,
    manifest: list[dict[str, Any]],
    encoder: Any,
    chunk_size: int,
) -> None:
    rows: list[tuple[str, str, int, bool]] = []
    for label, body in _section_chunks(soup):
        tokens = _count_tokens(encoder, body)
        rows.append(("section", label, tokens, tokens <= chunk_size))
    for unit in manifest:
        rows.append(
            (
                f"unit:{unit['kind']}",
                unit["html_id"],
                int(unit["tokens"]),
                bool(unit["fits_512"]),
            )
        )

    kind_w = max((len(r[0]) for r in rows), default=4)
    id_w = max((len(r[1]) for r in rows), default=2)
    kind_w = max(kind_w, 4)
    id_w = max(id_w, 2)
    print(f"{'kind':<{kind_w}}  {'id':<{id_w}}  {'tokens':>6}  fits_{chunk_size}")
    print(f"{'-' * kind_w}  {'-' * id_w}  {'-' * 6}  --------")
    for kind, html_id, tokens, fits in rows:
        print(
            f"{kind:<{kind_w}}  {html_id:<{id_w}}  {tokens:>6}  "
            f"{'yes' if fits else 'no'}"
        )


if __name__ == "__main__":
    main()
