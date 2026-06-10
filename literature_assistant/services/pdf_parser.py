"""PDF 解析服务（PyMuPDF）"""
import re
import fitz  # pymupdf


def extract_text(file_path: str) -> str:
    """使用 PyMuPDF 逐页提取文本，清洗页眉页脚"""
    doc = fitz.open(file_path)
    pages = []
    for page in doc:
        text = page.get_text()
        lines = []
        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.isdigit() and len(stripped) <= 4:
                continue
            lines.append(stripped)
        pages.append("\n".join(lines))
    doc.close()
    return "\n\n".join(pages)


def extract_metadata(file_path: str) -> dict:
    """从PDF元数据+正文中提取真实标题、作者等信息"""
    doc = fitz.open(file_path)

    # 1. 先尝试从PDF内置元数据获取
    meta = doc.metadata or {}
    pdf_title = (meta.get("title") or "").strip()
    pdf_author = (meta.get("author") or "").strip()
    pdf_subject = (meta.get("subject") or "").strip()
    pdf_keywords = (meta.get("keywords") or "").strip()

    # 2. 从正文第一页提取
    first_page_text = ""
    if doc.page_count > 0:
        first_page_text = doc[0].get_text()

    # 提取全文用于摘要
    full_text = extract_text(file_path)

    # 3. 标题：优先PDF元数据，否则取第一页最大字体文本
    title = pdf_title
    if not title:
        title = _extract_title_from_first_page(doc)
    if not title:
        # 回退：第一页前两行非空文本
        lines = [l.strip() for l in first_page_text.split("\n") if l.strip()]
        title = lines[0] if lines else "未知标题"

    # 4. 作者：优先PDF元数据
    authors = []
    if pdf_author:
        # 按逗号、分号、and拆分
        authors = re.split(r'[,;，；]|\band\b', pdf_author)
        authors = [a.strip() for a in authors if a.strip()]
    if not authors:
        authors = _extract_authors_from_text(first_page_text)
    if not authors:
        authors = ["未知作者"]

    # 5. 摘要
    abstract = _extract_abstract(full_text)

    # 6. 关键词
    keywords = []
    if pdf_keywords:
        keywords = re.split(r'[,;，；]', pdf_keywords)
        keywords = [k.strip() for k in keywords if k.strip()]
    if not keywords:
        keywords = _extract_keywords(full_text)

    # 7. 年份：从元数据或正文中找
    year = _extract_year(meta, full_text)

    doc.close()

    return {
        "title": title[:200],
        "authors": authors[:10],
        "abstract": abstract[:1000],
        "keywords": keywords[:10] if keywords else [],
        "year": year,
        "methods": _extract_section(full_text, ["方法", "method", "methodology", "材料与方法"]),
        "conclusions": _extract_section(full_text, ["结论", "conclusion", "结语"]),
        "innovations": "",
    }


def _extract_title_from_first_page(doc) -> str:
    """从第一页找最大字体的文本作为标题"""
    if doc.page_count == 0:
        return ""
    page = doc[0]
    blocks = page.get_text("dict")["blocks"]
    max_size = 0
    title_text = ""
    for block in blocks:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                if span["size"] > max_size and len(span["text"].strip()) > 3:
                    max_size = span["size"]
                    title_text = span["text"].strip()
    # 可能标题跨多个span，尝试合并同字号的连续文本
    if max_size > 0:
        parts = []
        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    if abs(span["size"] - max_size) < 0.5 and span["text"].strip():
                        parts.append(span["text"].strip())
        if parts:
            title_text = " ".join(parts)
    return title_text[:200]


def _extract_authors_from_text(first_page_text: str) -> list:
    """从第一页文本启发式提取作者（标题之后、摘要之前的行）"""
    lines = [l.strip() for l in first_page_text.split("\n") if l.strip()]
    if len(lines) < 2:
        return []
    # 跳过第一行（通常是标题），取后面几行直到遇到"abstract"/"摘要"等
    authors = []
    for line in lines[1:6]:
        low = line.lower()
        if any(kw in low for kw in ["abstract", "摘要", "关键词", "keyword", "introduction", "引言", "doi", "http"]):
            break
        # 作者行通常包含逗号分隔的人名，且不会太长
        if len(line) < 200 and not line[0].isdigit():
            # 过滤明显非作者行（太多汉字连续超过20字像正文）
            if re.search(r'[A-Z][a-z]+|[\u4e00-\u9fff]{2,4}', line):
                authors.append(line)
        if len(authors) >= 2:
            break
    if authors:
        # 尝试拆分
        combined = ", ".join(authors)
        parts = re.split(r'[,;，；、]|\band\b', combined)
        return [p.strip() for p in parts if p.strip() and len(p.strip()) < 40][:10]
    return []


def _extract_abstract(text: str) -> str:
    """提取摘要段落"""
    # 匹配 Abstract 或 摘要 后面的内容
    patterns = [
        r'(?:Abstract|ABSTRACT|摘\s*要)[：:\s]*(.{50,1000}?)(?:\n\s*(?:Key\s*words|关键词|Introduction|引言|1[\.\s]))',
        r'(?:Abstract|ABSTRACT|摘\s*要)[：:\s]*(.{50,800})',
    ]
    for pat in patterns:
        match = re.search(pat, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip().replace("\n", " ")
    return text[:500]


def _extract_keywords(text: str) -> list:
    """提取关键词"""
    patterns = [
        r'(?:Key\s*words|关键词)[：:\s]*(.{10,300})',
    ]
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            kw_text = match.group(1).strip()
            # 到换行或下一节为止
            kw_text = kw_text.split("\n")[0]
            parts = re.split(r'[,;，；、]', kw_text)
            return [p.strip() for p in parts if p.strip() and len(p.strip()) < 30][:10]
    return []


def _extract_year(meta: dict, text: str) -> int | None:
    """提取发表年份"""
    # 从元数据日期
    for key in ["creationDate", "modDate"]:
        val = meta.get(key, "")
        if val:
            match = re.search(r'(19|20)\d{2}', val)
            if match:
                return int(match.group())
    # 从正文前500字中找年份
    match = re.search(r'(20[012]\d|19[89]\d)', text[:500])
    if match:
        return int(match.group())
    return None


def _extract_section(text: str, section_names: list) -> str:
    """提取指定章节的简短内容"""
    for name in section_names:
        pat = rf'(?:^|\n)\s*(?:\d+[\.\s]*)?\s*{name}[：:\s]*\n(.{{30,500}})'
        match = re.search(pat, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip().replace("\n", " ")[:300]
    return ""
