"""引用格式转换服务。"""
import json


def _parse_authors(authors) -> list[str]:
    if isinstance(authors, str):
        try:
            parsed = json.loads(authors)
            if isinstance(parsed, list):
                return [str(author) for author in parsed if author]
        except (json.JSONDecodeError, TypeError):
            return [authors] if authors else ["未知作者"]
        return [authors] if authors else ["未知作者"]

    if isinstance(authors, list):
        return [str(author) for author in authors if author] or ["未知作者"]

    return ["未知作者"]


def _get_title(paper: dict) -> str:
    return paper.get("title") or paper.get("filename") or "未知标题"


def _get_year(paper: dict) -> str:
    return str(paper.get("year") or "n.d.")


def format_gbt(paper: dict) -> str:
    authors = _parse_authors(paper.get("authors"))
    title = _get_title(paper)
    year = _get_year(paper)
    author_text = ", ".join(authors[:3])
    if len(authors) > 3:
        author_text += ", 等"
    return f"{author_text}. {title}[J]. [CITE NEEDED], {year}."


def format_apa(paper: dict) -> str:
    authors = _parse_authors(paper.get("authors"))
    title = _get_title(paper)
    year = _get_year(paper)
    author_text = ", ".join(authors[:3])
    if len(authors) > 3:
        author_text += ", et al."
    return f"{author_text} ({year}). {title}. [CITE NEEDED]."


def format_ieee(paper: dict) -> str:
    authors = _parse_authors(paper.get("authors"))
    title = _get_title(paper)
    year = _get_year(paper)
    author_text = ", ".join(authors[:3])
    if len(authors) > 3:
        author_text += ", et al."
    return f'{author_text}, "{title}," [CITE NEEDED], {year}.'


def format_mla(paper: dict) -> str:
    authors = _parse_authors(paper.get("authors"))
    title = _get_title(paper)
    year = _get_year(paper)
    author_text = authors[0] if authors else "未知作者"
    return f'{author_text}. "{title}." [CITE NEEDED], {year}.'


def format_all(paper: dict) -> dict:
    return {
        "gbt": format_gbt(paper),
        "apa": format_apa(paper),
        "ieee": format_ieee(paper),
        "mla": format_mla(paper),
    }


def format_bibliography(papers: list, style: str = "gbt") -> str:
    formatters = {
        "gbt": format_gbt,
        "apa": format_apa,
        "ieee": format_ieee,
        "mla": format_mla,
    }
    formatter = formatters.get(style, format_gbt)
    lines = [f"[{index}] {formatter(paper)}" for index, paper in enumerate(papers, start=1)]
    return "\n".join(lines)
