document.addEventListener("DOMContentLoaded", () => {
    const papersBox = document.getElementById("citation-papers");
    const resultBox = document.getElementById("citation-result");
    const formatButton = document.getElementById("btn-format");
    const copyButton = document.getElementById("btn-copy-cite");
    const exportButton = document.getElementById("btn-export");

    function selectedPaperIds() {
        return Array.from(papersBox.querySelectorAll("input:checked")).map((element) => Number(element.value));
    }

    async function loadPapers() {
        try {
            const response = await fetch("/api/citation/papers");
            const data = await response.json();
            const papers = data.data || [];

            if (!papers.length) {
                papersBox.innerHTML = '<p class="empty-hint">暂无可用于引用格式化的已解析文献。</p>';
                return;
            }

            papersBox.innerHTML = papers.map((paper) => {
                const title = paper.title || paper.filename || "未命名文献";
                return `
                    <label class="checkbox-item">
                        <input type="checkbox" value="${paper.id}">
                        <span>${window.appEscapeHtml(title)}</span>
                    </label>
                `;
            }).join("");
        } catch (error) {
            papersBox.innerHTML = '<p class="empty-hint">文献列表加载失败。</p>';
        }
    }

    async function formatCitation() {
        const paperIds = selectedPaperIds();
        const style = document.querySelector('input[name="style"]:checked')?.value || "gbt";

        if (!paperIds.length) {
            window.appNotify("请至少选择一篇文献", "warning");
            return;
        }

        formatButton.disabled = true;
        formatButton.textContent = "生成中...";

        try {
            const response = await fetch("/api/citation/format", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ paper_ids: paperIds, style }),
            });
            const data = await response.json();

            if (data.code !== 0) {
                window.appNotify(data.message || "生成失败", "error");
                return;
            }

            resultBox.textContent = data.data?.bibliography || "";
            exportButton.style.display = resultBox.textContent ? "inline-flex" : "none";
            window.appNotify("引用列表已生成", "success");
        } catch (error) {
            window.appNotify("生成失败，请稍后重试", "error");
        } finally {
            formatButton.disabled = false;
            formatButton.textContent = "生成引用列表";
        }
    }

    async function exportCitation() {
        const paperIds = selectedPaperIds();
        const style = document.querySelector('input[name="style"]:checked')?.value || "gbt";

        if (!paperIds.length) {
            window.appNotify("请先选择文献", "warning");
            return;
        }

        try {
            const response = await fetch("/api/citation/export", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ paper_ids: paperIds, style }),
            });
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = `references_${style}.txt`;
            link.click();
            URL.revokeObjectURL(url);
            window.appNotify("引用文件已导出", "success");
        } catch (error) {
            window.appNotify("导出失败，请稍后重试", "error");
        }
    }

    formatButton?.addEventListener("click", formatCitation);
    copyButton?.addEventListener("click", () => window.appCopyText(resultBox.textContent, "引用列表已复制"));
    exportButton?.addEventListener("click", exportCitation);

    loadPapers();
});
