document.addEventListener("DOMContentLoaded", () => {
    const designButton = document.getElementById("btn-design");
    const resultContainer = document.getElementById("experiment-result");
    const flowStepsContainer = document.getElementById("flow-steps-container");
    const historyContainer = document.getElementById("experiment-history");
    const goalInput = document.getElementById("goal");
    const hypothesisInput = document.getElementById("hypothesis");
    const paperOptions = document.getElementById("experiment-paper-options");
    const recommendGoalButton = document.getElementById("btn-recommend-goal");
    const recommendHypothesisButton = document.getElementById("btn-recommend-hypothesis");

    function renderList(items) {
        if (!items || !items.length) {
            return "未提供";
        }
        return items.map((item) => window.appEscapeHtml(item)).join("、");
    }

    function renderFlowSteps(steps) {
        if (!steps || !steps.length) {
            flowStepsContainer.innerHTML = "";
            return;
        }

        flowStepsContainer.innerHTML = `
            <h4>实验流程</h4>
            <div class="flow-steps">
                ${steps.map((step, index) => `
                    <div class="flow-step">
                        <span class="flow-step-index">${index + 1}</span>
                        <div class="flow-step-text">${window.appEscapeHtml(step)}</div>
                    </div>
                `).join("")}
            </div>
        `;
    }

    function renderResult(data) {
        resultContainer.innerHTML = `
            <div class="result-grid">
                <div class="result-card">
                    <h4>实验变量</h4>
                    <p><strong>自变量：</strong>${renderList(data.variables?.independent)}</p>
                    <p><strong>因变量：</strong>${renderList(data.variables?.dependent)}</p>
                    <p><strong>控制变量：</strong>${renderList(data.variables?.controlled)}</p>
                </div>
                <div class="result-card">
                    <h4>样本设计</h4>
                    <p><strong>建议样本量：</strong>${window.appEscapeHtml(String(data.sample?.size || "未提供"))}</p>
                    <p><strong>计算依据：</strong>${window.appEscapeHtml(data.sample?.calculation_basis || "未提供")}</p>
                    <p><strong>分组方案：</strong>${renderList(data.sample?.groups)}</p>
                    <p><strong>随机化：</strong>${window.appEscapeHtml(data.sample?.randomization || "未提供")}</p>
                </div>
                <div class="result-card">
                    <h4>统计分析</h4>
                    <p><strong>主要方法：</strong>${window.appEscapeHtml(data.statistics?.primary_method || "未提供")}</p>
                    <p><strong>推荐软件：</strong>${window.appEscapeHtml(data.statistics?.software || "未提供")}</p>
                    <p><strong>显著性水平：</strong>${window.appEscapeHtml(String(data.statistics?.significance_level || "未提供"))}</p>
                </div>
                <div class="result-card">
                    <h4>潜在风险</h4>
                    <ul>${(data.risks || []).map((risk) => `<li>${window.appEscapeHtml(risk)}</li>`).join("") || "<li>未提供</li>"}</ul>
                </div>
            </div>
        `;

        renderFlowSteps(data.flow_steps || []);
    }

    function selectedPaperId() {
        const checked = paperOptions?.querySelector('input[name="experiment-paper"]:checked');
        if (!checked || !checked.value) {
            return null;
        }
        return Number(checked.value);
    }

    async function loadPapers() {
        if (!paperOptions) {
            return;
        }

        try {
            const response = await fetch("/api/papers");
            const data = await response.json();
            const papers = (data.data || []).filter((paper) => paper.parse_status === "done");

            if (!papers.length) {
                paperOptions.innerHTML = '<p class="empty-hint">暂无已解析文献。你仍然可以只基于研究目标生成实验草案。</p>';
                return;
            }

            paperOptions.innerHTML = `
                <label class="checkbox-item">
                    <input type="radio" name="experiment-paper" value="" checked>
                    <span>不选择参考文献</span>
                </label>
                ${papers.map((paper) => {
                    const title = paper.title || paper.filename || "未命名文献";
                    return `
                        <label class="checkbox-item">
                            <input type="radio" name="experiment-paper" value="${paper.id}">
                            <span>${window.appEscapeHtml(title)}</span>
                        </label>
                    `;
                }).join("")}
            `;
        } catch (error) {
            paperOptions.innerHTML = '<p class="empty-hint">文献列表加载失败。你仍然可以只基于研究目标生成实验草案。</p>';
        }
    }

    async function loadHistory() {
        try {
            const response = await fetch("/api/experiment/list");
            const data = await response.json();
            const items = data.code === 0 ? (data.data || []) : [];

            if (!items.length) {
                historyContainer.innerHTML = '<p class="empty-hint">暂无实验草案记录。</p>';
                return;
            }

            historyContainer.innerHTML = items.map((item) => `
                <div class="history-item experiment-history-item" data-id="${item.id}">
                    <span class="history-topic">${window.appEscapeHtml(item.goal || "未命名实验")}</span>
                    <span class="history-date">${window.appEscapeHtml(item.created_at || "-")}</span>
                </div>
            `).join("");

            historyContainer.querySelectorAll(".experiment-history-item").forEach((element) => {
                element.addEventListener("click", () => {
                    const matched = items.find((item) => String(item.id) === String(element.dataset.id));
                    if (matched?.content) {
                        renderResult(matched.content);
                    }
                });
            });
        } catch (error) {
            historyContainer.innerHTML = '<p class="empty-hint">实验历史加载失败。</p>';
        }
    }

    async function recommendInput(field, button) {
        const paperId = selectedPaperId();
        if (!paperId) {
            window.appNotify("请先选择一篇参考文献", "warning");
            return;
        }

        const originalText = button.textContent;
        button.disabled = true;
        button.textContent = "生成中...";

        try {
            const response = await fetch("/api/experiment/recommend-input", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    field,
                    paper_id: paperId,
                    goal: goalInput.value.trim(),
                }),
            });
            const data = await response.json();

            if (data.code !== 0) {
                window.appNotify(data.message || "AI生成失败", "error");
                return;
            }

            const text = data.data?.text || "";
            if (field === "goal") {
                goalInput.value = text;
            } else {
                hypothesisInput.value = text;
            }
            window.appNotify("AI 已生成输入内容", "success");
        } catch (error) {
            window.appNotify("AI生成失败，请稍后重试", "error");
        } finally {
            button.disabled = false;
            button.textContent = originalText;
        }
    }

    designButton?.addEventListener("click", async () => {
        const goal = goalInput.value.trim();
        const hypothesis = hypothesisInput.value.trim();
        const paperId = selectedPaperId();

        if (!goal) {
            window.appNotify("请先输入研究目标", "warning");
            return;
        }

        designButton.disabled = true;
        designButton.textContent = "正在生成...";
        resultContainer.innerHTML = "";
        flowStepsContainer.innerHTML = "";

        try {
            const response = await fetch("/api/experiment/design", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ goal, hypothesis, paper_id: paperId }),
            });
            const data = await response.json();

            if (data.code !== 0) {
                window.appNotify(data.message || "生成失败", "error");
                return;
            }

            renderResult(data.data || {});
            window.appNotify("实验草案已生成", "success");
            loadHistory();
        } catch (error) {
            window.appNotify("生成失败，请稍后重试", "error");
        } finally {
            designButton.disabled = false;
            designButton.textContent = "生成实验草案";
        }
    });

    recommendGoalButton?.addEventListener("click", () => recommendInput("goal", recommendGoalButton));
    recommendHypothesisButton?.addEventListener("click", () => recommendInput("hypothesis", recommendHypothesisButton));

    loadPapers();
    loadHistory();
});
