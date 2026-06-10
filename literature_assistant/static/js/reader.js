import * as pdfjsLib from "/static/vendor/pdfjs/pdf.min.mjs";
import * as pdfjsViewer from "/static/vendor/pdfjs/pdf_viewer.min.mjs";

pdfjsLib.GlobalWorkerOptions.workerSrc = "/static/vendor/pdfjs/pdf.worker.min.mjs";

let readerPaperId = null;
let pdfDoc = null;
let pdfViewer = null;
let eventBus = null;
let linkService = null;
let readerAnnotations = [];
const legacyRectRatioCache = new Map();

document.addEventListener("DOMContentLoaded", async () => {
    readerPaperId = window.PAPER_ID;
    initToolbar();
    initPdfViewer();
    await Promise.all([loadAnnotations(), loadPdf()]);
});

function initToolbar() {
    document.getElementById("btn-highlight")?.addEventListener("click", () => saveSelection("highlight"));
    document.getElementById("btn-clear-page-highlights")?.addEventListener("click", clearCurrentPageHighlights);
    document.getElementById("btn-annotate")?.addEventListener("click", () => saveSelection("note"));
    document.getElementById("btn-translate")?.addEventListener("click", translateSelected);
    document.getElementById("btn-summary")?.addEventListener("click", summarizePdf);
    document.getElementById("btn-zoom-out")?.addEventListener("click", () => zoomPdf(-0.12));
    document.getElementById("btn-zoom-in")?.addEventListener("click", () => zoomPdf(0.12));
    document.getElementById("btn-fit-width")?.addEventListener("click", fitPdfWidth);
}

function initPdfViewer() {
    const shell = document.getElementById("pdf-shell");
    shell.innerHTML = '<div id="pdf-viewer-container" class="pdf-viewer-container"><div id="pdf-viewer" class="pdfViewer"></div></div>';
    const container = document.getElementById("pdf-viewer-container");
    const viewer = document.getElementById("pdf-viewer");

    eventBus = new pdfjsViewer.EventBus();
    linkService = new pdfjsViewer.PDFLinkService({ eventBus });
    pdfViewer = new pdfjsViewer.PDFViewer({
        container,
        viewer,
        eventBus,
        linkService,
        textLayerMode: 1,
    });
    linkService.setViewer(pdfViewer);

    eventBus.on("pagesinit", () => {
        fitPdfWidth();
    });

    eventBus.on("scalechanging", () => {
        updateZoomLabel();
        window.setTimeout(applyAnnotationsToAllPages, 80);
    });

    eventBus.on("textlayerrendered", ({ pageNumber }) => {
        applyAnnotationsToPage(pageNumber - 1);
    });

    eventBus.on("pagerendered", ({ pageNumber }) => {
        applyAnnotationsToPage(pageNumber - 1);
    });

    window.addEventListener("resize", debounce(applyAnnotationsToAllPages, 120));
}

function fitPdfWidth() {
    if (!pdfViewer) {
        return;
    }
    pdfViewer.currentScaleValue = "page-width";
    updateZoomLabel("适宽");
}

function zoomPdf(delta) {
    if (!pdfViewer) {
        return;
    }

    const currentScale = Number(pdfViewer.currentScale) || 1;
    const nextScale = Math.max(0.75, Math.min(2.4, currentScale + delta));
    pdfViewer.currentScaleValue = String(nextScale);
    updateZoomLabel();
}

function updateZoomLabel(forcedLabel = "") {
    const label = document.getElementById("zoom-level");
    if (!label || !pdfViewer) {
        return;
    }

    if (forcedLabel) {
        label.textContent = forcedLabel;
        return;
    }

    const currentScale = Number(pdfViewer.currentScale) || 1;
    label.textContent = `${Math.round(currentScale * 100)}%`;
}

async function loadPdf() {
    try {
        const loadingTask = pdfjsLib.getDocument(`/api/reader/${readerPaperId}/file`);
        pdfDoc = await loadingTask.promise;
        document.getElementById("total-pages").textContent = String(pdfDoc.numPages);
        pdfViewer.setDocument(pdfDoc);
        linkService.setDocument(pdfDoc, null);
        updateZoomLabel("适宽");
    } catch (error) {
        document.getElementById("pdf-shell").innerHTML = '<div class="reader-loading">PDF加载失败</div>';
        window.appNotify("PDF加载失败", "error");
    }
}

async function loadAnnotations() {
    try {
        const response = await fetch(`/api/reader/${readerPaperId}/annotations`);
        const data = await response.json();
        readerAnnotations = data.code === 0 ? (data.data || []) : [];
        renderNotes();
        applyAnnotationsToAllPages();
    } catch (error) {
        readerAnnotations = [];
        renderNotes();
    }
}

function applyAnnotationsToAllPages() {
    if (!pdfViewer) {
        return;
    }
    for (let pageIndex = 0; pageIndex < (pdfDoc?.numPages || 0); pageIndex += 1) {
        applyAnnotationsToPage(pageIndex);
    }
}

function applyAnnotationsToPage(pageIndex) {
    const pageView = pdfViewer?.getPageView?.(pageIndex);
    const textLayerDiv = pageView?.textLayer?.div || pageView?.textLayerDiv || pageView?.div?.querySelector(".textLayer");
    if (!textLayerDiv) {
        return;
    }

    const overlayHost = pageView?.div || textLayerDiv.parentElement;
    const pageRect = overlayHost?.getBoundingClientRect();
    const pageWidth = pageRect?.width || overlayHost?.clientWidth || 0;
    const pageHeight = pageRect?.height || overlayHost?.clientHeight || 0;
    if (!overlayHost || pageWidth <= 0 || pageHeight <= 0) {
        return;
    }

    const oldOverlays = overlayHost.querySelectorAll(`.annotation-overlay[data-page="${pageIndex}"]`) || [];
    oldOverlays.forEach((node) => node.remove());

    const pageAnnotations = readerAnnotations.filter((annotation) => Number(annotation.page_index) === pageIndex);
    for (const annotation of pageAnnotations) {
        let rects = [];
        try {
            rects = annotation.selector_json ? JSON.parse(annotation.selector_json) : [];
        } catch {
            rects = [];
        }

        if (!Array.isArray(rects) || rects.length === 0) {
            continue;
        }

        for (const [rectIndex, rect] of rects.entries()) {
            const displayRect = resolveAnnotationRect(rect, pageWidth, pageHeight, buildLegacyRectCacheKey(annotation, pageIndex, rectIndex, rect));
            if (!displayRect) {
                continue;
            }
            const overlay = document.createElement("div");
            overlay.className = annotation.type === "highlight" ? "annotation-overlay annotation-highlight" : "annotation-overlay annotation-note";
            overlay.dataset.page = String(pageIndex);
            overlay.dataset.id = String(annotation.id || "");
            overlay.style.left = `${displayRect.left}px`;
            overlay.style.top = `${displayRect.top + Math.max(1, displayRect.height * 0.14)}px`;
            overlay.style.width = `${displayRect.width}px`;
            overlay.style.height = `${Math.max(2, displayRect.height * 0.68)}px`;
            overlay.style.setProperty("--highlight-color", annotation.color || "#f6e58d");
            overlay.style.borderColor = annotation.color || "#f6e58d";
            overlay.title = annotation.note || annotation.text || "";
            overlayHost.appendChild(overlay);
        }
    }
}

function resolveAnnotationRect(rect, pageWidth, pageHeight, legacyCacheKey = "") {
    if (!rect) {
        return null;
    }

    const hasRatio = [rect.leftRatio, rect.topRatio, rect.widthRatio, rect.heightRatio].every((value) => typeof value === "number");
    if (hasRatio) {
        return {
            left: rect.leftRatio * pageWidth,
            top: rect.topRatio * pageHeight,
            width: rect.widthRatio * pageWidth,
            height: rect.heightRatio * pageHeight,
        };
    }

    const hasStoredPageSize = typeof rect.pageWidth === "number" && rect.pageWidth > 0 && typeof rect.pageHeight === "number" && rect.pageHeight > 0;
    if (hasStoredPageSize && typeof rect.left === "number" && typeof rect.top === "number" && typeof rect.width === "number" && typeof rect.height === "number") {
        const scaleX = pageWidth / rect.pageWidth;
        const scaleY = pageHeight / rect.pageHeight;
        return {
            left: rect.left * scaleX,
            top: rect.top * scaleY,
            width: rect.width * scaleX,
            height: rect.height * scaleY,
        };
    }

    if (typeof rect.left === "number" && typeof rect.top === "number" && typeof rect.width === "number" && typeof rect.height === "number") {
        if (legacyCacheKey) {
            if (!legacyRectRatioCache.has(legacyCacheKey)) {
                legacyRectRatioCache.set(legacyCacheKey, {
                    leftRatio: rect.left / pageWidth,
                    topRatio: rect.top / pageHeight,
                    widthRatio: rect.width / pageWidth,
                    heightRatio: rect.height / pageHeight,
                });
            }
            const cached = legacyRectRatioCache.get(legacyCacheKey);
            return {
                left: cached.leftRatio * pageWidth,
                top: cached.topRatio * pageHeight,
                width: cached.widthRatio * pageWidth,
                height: cached.heightRatio * pageHeight,
            };
        }

        return {
            left: rect.left,
            top: rect.top,
            width: rect.width,
            height: rect.height,
        };
    }

    return null;
}

function buildLegacyRectCacheKey(annotation, pageIndex, rectIndex, rect) {
    if (!annotation?.id || !rect) {
        return "";
    }

    return [
        annotation.id,
        pageIndex,
        rectIndex,
        rect.left,
        rect.top,
        rect.width,
        rect.height,
    ].join(":");
}

function getSelectionRectData() {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0 || selection.isCollapsed) {
        return null;
    }

    const text = selection.toString().trim();
    if (!text) {
        return null;
    }

    const range = selection.getRangeAt(0);
    const rectList = Array.from(range.getClientRects()).filter((rect) => rect.width > 0 && rect.height > 0);
    if (!rectList.length) {
        return null;
    }

    const firstNode = range.startContainer?.nodeType === Node.ELEMENT_NODE
        ? range.startContainer
        : range.startContainer?.parentElement;
    const pageNode = firstNode?.closest(".page");
    if (!pageNode) {
        return null;
    }

    const pageNumber = Number(pageNode.dataset.pageNumber || 1);
    const pageRect = pageNode.getBoundingClientRect();
    const pageWidth = pageRect.width || pageNode.clientWidth;
    const pageHeight = pageRect.height || pageNode.clientHeight;
    if (pageWidth <= 0 || pageHeight <= 0) {
        return null;
    }

    const normalizedRects = rectList
        .filter((rect) => rect.bottom >= pageRect.top && rect.top <= pageRect.bottom)
        .map((rect) => {
            const left = rect.left - pageRect.left;
            const top = rect.top - pageRect.top;
            return {
                left,
                top,
                width: rect.width,
                height: rect.height,
                leftRatio: left / pageWidth,
                topRatio: top / pageHeight,
                widthRatio: rect.width / pageWidth,
                heightRatio: rect.height / pageHeight,
                pageWidth,
                pageHeight,
            };
        });

    if (!normalizedRects.length) {
        return null;
    }

    return {
        text,
        pageIndex: pageNumber - 1,
        rects: normalizedRects,
    };
}

async function saveSelection(type) {
    const selectionData = getSelectionRectData();
    if (!selectionData) {
        window.appNotify("请先在 PDF 文本层中选中内容", "warning");
        return;
    }

    let note = "";
    if (type === "note") {
        note = (await window.appPrompt("添加批注", "", {
            placeholder: "请输入批注内容",
        }))?.trim() || "";
        if (!note) {
            return;
        }
    }

    const color = document.getElementById("highlight-color").value;
    try {
        const response = await fetch("/api/reader/annotation", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                paper_id: readerPaperId,
                type,
                text: selectionData.text,
                note,
                color,
                page_index: selectionData.pageIndex,
                char_start: 0,
                char_end: selectionData.text.length,
                selector_json: JSON.stringify(selectionData.rects),
            }),
        });
        const data = await response.json();
        if (data.code !== 0) {
            window.appNotify(data.message || "保存失败", "error");
            return;
        }

        clearSelection();
        await loadAnnotations();
        window.appNotify(type === "note" ? "批注已保存" : "高亮已保存", "success");
    } catch (error) {
        window.appNotify("保存失败，请稍后重试", "error");
    }
}

function renderNotes() {
    const noteContainer = document.getElementById("annotations-list");
    const items = readerAnnotations.filter((annotation) => annotation.type === "note" || annotation.type === "highlight");

    if (!items.length) {
        noteContainer.innerHTML = '<p class="empty-hint">暂时还没有高亮或批注。</p>';
        return;
    }

    noteContainer.innerHTML = items.map((item) => {
        const isHighlight = item.type === "highlight";
        return `
        <div class="annotation-item ${isHighlight ? "annotation-item-highlight" : ""}" style="border-left:3px solid ${item.color || "#f6e58d"};">
            <div class="ann-type">${isHighlight ? "高亮" : "批注"} · P${Number(item.page_index) + 1}</div>
            <div class="ann-text">“${window.appEscapeHtml((item.text || "").slice(0, 96))}”</div>
            ${isHighlight ? "" : `<div class="ann-note">${window.appEscapeHtml(item.note || "无附加说明")}</div>`}
            <div class="actions-bar">
                <button class="btn-secondary ann-jump" data-page="${item.page_index}">定位</button>
                <button class="ann-delete" data-id="${item.id}">${isHighlight ? "清除高亮" : "删除批注"}</button>
            </div>
        </div>
    `;
    }).join("");

    noteContainer.querySelectorAll(".ann-delete").forEach((button) => {
        button.addEventListener("click", () => deleteAnnotation(Number(button.dataset.id)));
    });
    noteContainer.querySelectorAll(".ann-jump").forEach((button) => {
        button.addEventListener("click", () => jumpToPage(Number(button.dataset.page)));
    });
}

function jumpToPage(pageIndex) {
    const pageView = pdfViewer?.getPageView?.(pageIndex);
    pageView?.div?.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function translateSelected() {
    const selectionData = getSelectionRectData();
    if (!selectionData) {
        window.appNotify("请先选中文本后再翻译", "warning");
        return;
    }

    const targetLang = document.getElementById("translate-lang").value;
    try {
        const response = await fetch("/api/reader/translate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ paper_id: readerPaperId, text: selectionData.text, target_lang: targetLang }),
        });
        const data = await response.json();
        if (data.code !== 0) {
            window.appNotify(data.message || "翻译失败", "error");
            return;
        }

        const box = document.getElementById("translation-box");
        const empty = document.getElementById("translation-empty");
        box.style.display = "block";
        box.textContent = data.data.translated || "";
        empty.style.display = "none";
        clearSelection();
    } catch (error) {
        window.appNotify("翻译失败，请稍后重试", "error");
    }
}

async function summarizePdf() {
    try {
        const response = await fetch("/api/reader/summary", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ paper_id: readerPaperId }),
        });
        const data = await response.json();
        if (data.code !== 0) {
            window.appNotify(data.message || "总结失败", "error");
            return;
        }

        const box = document.getElementById("summary-box");
        const empty = document.getElementById("summary-empty");
        box.style.display = "block";
        box.textContent = data.data.summary || "";
        empty.style.display = "none";
        window.appNotify("PDF 总结已生成", "success");
    } catch (error) {
        window.appNotify("总结失败，请稍后重试", "error");
    }
}

async function deleteAnnotation(id) {
    await deleteAnnotationsByIds([id], "已删除");
}

async function clearCurrentPageHighlights() {
    const currentPageIndex = Math.max(0, Number(pdfViewer?.currentPageNumber || 1) - 1);
    const highlights = readerAnnotations.filter((annotation) => (
        annotation.type === "highlight"
        && Number(annotation.page_index) === currentPageIndex
        && annotation.id
    ));

    if (!highlights.length) {
        window.appNotify(`第 ${currentPageIndex + 1} 页没有高亮`, "info");
        return;
    }

    const confirmed = await window.appConfirm("清除本页高亮", {
        message: `将删除第 ${currentPageIndex + 1} 页的 ${highlights.length} 条高亮，批注不会删除。`,
        confirmText: "清除",
        cancelText: "取消",
    });

    if (!confirmed) {
        return;
    }

    await deleteAnnotationsByIds(highlights.map((annotation) => annotation.id), "本页高亮已清除");
}

async function deleteAnnotationsByIds(ids, successMessage) {
    const validIds = ids.map(Number).filter((id) => Number.isFinite(id) && id > 0);
    if (!validIds.length) {
        return;
    }

    try {
        for (const id of validIds) {
            const response = await fetch(`/api/reader/annotation/${id}`, { method: "DELETE" });
            const data = await response.json();
            if (data.code !== 0) {
                window.appNotify(data.message || "删除失败", "error");
                return;
            }
        }

        await loadAnnotations();
        window.appNotify(successMessage, "success");
    } catch (error) {
        window.appNotify("删除失败，请稍后重试", "error");
    }
}

function clearSelection() {
    const selection = window.getSelection();
    selection?.removeAllRanges();
}

function debounce(callback, delay) {
    let timer = null;
    return (...args) => {
        window.clearTimeout(timer);
        timer = window.setTimeout(() => callback(...args), delay);
    };
}
