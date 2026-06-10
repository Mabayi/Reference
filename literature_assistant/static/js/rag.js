document.addEventListener("DOMContentLoaded", () => {
    const searchButton = document.getElementById("btn-rag-search");
    const queryInput = document.getElementById("rag-query");
    const topKInput = document.getElementById("rag-topk");
    const resultContainer = document.getElementById("rag-results");

    async function search() {
        const query = queryInput.value.trim();
        const topK = Number(topKInput.value || 5);

        if (!query) {
            window.appNotify("请先输入检索问题", "warning");
            return;
        }

        searchButton.disabled = true;
        searchButton.textContent = "检索中...";

        try {
            const response = await fetch("/api/rag/search", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query, top_k: topK }),
            });
            const data = await response.json();
            const results = data.code === 0 ? (data.data || []) : [];

            if (!results.length) {
                resultContainer.innerHTML = '<p class="empty-hint">没有检索到匹配片段。</p>';
                return;
            }

            resultContainer.innerHTML = results.map((item, index) => `
                <div class="glass-card" style="padding:18px; margin-bottom:12px;">
                    <p><strong>结果 ${index + 1}</strong> · 文献 ${window.appEscapeHtml(String(item.paper_id))} · 分数 ${window.appEscapeHtml(String(item.score))}</p>
                    <div class="output-area" style="min-height:auto; margin-top:10px;">${window.appEscapeHtml(item.text || "")}</div>
                </div>
            `).join("");
        } catch (error) {
            resultContainer.innerHTML = '<p class="empty-hint">检索失败，请稍后重试。</p>';
        } finally {
            searchButton.disabled = false;
            searchButton.textContent = "开始检索";
        }
    }

    searchButton?.addEventListener("click", search);
});
