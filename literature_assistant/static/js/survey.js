document.addEventListener("DOMContentLoaded", () => {
    const topicInput = document.getElementById("topic");
    const paperCheckboxes = document.getElementById("paper-checkboxes");
    const generateButton = document.getElementById("btn-generate");
    const recommendTopicButton = document.getElementById("btn-recommend-topic");
    const topicRecommendation = document.getElementById("topic-recommendation");
    const surveyOutputShell = document.getElementById("survey-output-shell");
    const surveyOutput = document.getElementById("survey-output");
    const surveyActions = document.getElementById("survey-actions");
    const historyList = document.getElementById("history-list");
    const copyButton = document.getElementById("btn-copy-survey");
    const toggleButton = document.getElementById("btn-toggle-survey");

    let surveyRawText = "";
    let surveyManuallyExpanded = false;
    let recommendedTopic = "";

    function cleanSurveyText(value) {
        return String(value || "")
            .replace(/\*\*/g, "")
            .replace(/\*/g, "")
            .replace(/`{1,3}/g, "")
            .replace(/^\s{0,3}#{1,6}\s*/gm, "")
            .replace(/^\s*[-*_]{3,}\s*$/gm, "")
            .replace(/^\s*[-*+•●▪◆·]\s+/gm, "")
            .replace(/^\s*\d+[.)、]\s+/gm, "")
            .replace(/^\s*>\s?/gm, "")
            .replace(/\[(.*?)\]\((.*?)\)/g, "$1")
            .replace(/[ \t]+\n/g, "\n")
            .replace(/\n{3,}/g, "\n\n")
            .replace(/^\s+/, "");
    }

    function setSurveyText(value) {
        surveyRawText = cleanSurveyText(value);
        surveyOutput.textContent = surveyRawText;
        updateSurveyCollapse();
    }

    function setSurveyExpanded(expanded) {
        surveyOutputShell?.classList.toggle("is-expanded", expanded);
        surveyOutputShell?.classList.toggle("is-collapsed", !expanded);
        if (toggleButton) {
            toggleButton.textContent = expanded ? "收起内容" : "展开全文";
        }
        if (copyButton) {
            copyButton.style.display = expanded && surveyRawText.trim() ? "inline-flex" : "none";
        }
    }

    function resetSurveyExpansion() {
        surveyManuallyExpanded = false;
        setSurveyExpanded(false);
    }

    function updateSurveyCollapse() {
        if (!surveyOutputShell || !surveyOutput) {
            return;
        }
        const canCollapse = surveyOutput.scrollHeight > 360;
        surveyOutputShell.classList.toggle("can-collapse", canCollapse);
        if (!canCollapse) {
            setSurveyExpanded(true);
            if (toggleButton) {
                toggleButton.style.display = "none";
            }
            return;
        }
        if (toggleButton) {
            toggleButton.style.display = "inline-flex";
        }
        setSurveyExpanded(surveyManuallyExpanded);
    }

    function selectedPaperIds() {
        return Array.from(paperCheckboxes.querySelectorAll("input:checked")).map((element) => Number(element.value));
    }

    function updateGenerateButton() {
        const hasTopic = Boolean(topicInput.value.trim());
        generateButton.disabled = !hasTopic;
    }

    function clearTopicRecommendation() {
        recommendedTopic = "";
        if (topicRecommendation) {
            topicRecommendation.style.display = "none";
            topicRecommendation.innerHTML = "";
        }
    }

    function renderTopicRecommendation(topic) {
        recommendedTopic = String(topic || "").trim();
        if (!topicRecommendation || !recommendedTopic) {
            clearTopicRecommendation();
            return;
        }

        topicRecommendation.style.display = "flex";
        topicRecommendation.innerHTML = `
            <span>推荐主题：${window.appEscapeHtml(recommendedTopic)}</span>
            <button class="btn-secondary topic-apply-btn" type="button">采用</button>
        `;
    }

    async function loadPapers() {
        try {
            const response = await fetch("/api/papers");
            const data = await response.json();
            const papers = (data.data || []).filter((paper) => paper.parse_status === "done");

            if (!papers.length) {
                paperCheckboxes.innerHTML = '<p class="empty-hint">暂无已解析文献。你仍然可以只输入研究主题生成综述框架；如果先上传并解析文献，结果会更具体。</p>';
                updateGenerateButton();
                return;
            }

            paperCheckboxes.innerHTML = papers.map((paper) => {
                const title = paper.title || paper.filename || "未命名文献";
                return `
                    <label class="checkbox-item">
                        <input type="checkbox" value="${paper.id}">
                        <span>${window.appEscapeHtml(title)}</span>
                    </label>
                `;
            }).join("");

            updateGenerateButton();
        } catch (error) {
            paperCheckboxes.innerHTML = '<p class="empty-hint">文献列表加载失败。你仍然可以先输入研究主题尝试生成。</p>';
            updateGenerateButton();
        }
    }

    async function loadHistory() {
        try {
            const response = await fetch("/api/survey/list");
            const data = await response.json();
            const surveys = data.data || [];

            if (!surveys.length) {
                historyList.innerHTML = '<p class="empty-hint">暂时还没有生成记录。</p>';
                return;
            }

            historyList.innerHTML = surveys.map((survey) => `
                <div class="history-item" data-id="${survey.id}">
                    <span class="history-topic">${window.appEscapeHtml(survey.topic)}</span>
                    <span class="history-date">${window.appEscapeHtml(survey.created_at)}</span>
                </div>
            `).join("");
        } catch (error) {
            historyList.innerHTML = '<p class="empty-hint">历史记录加载失败。</p>';
        }
    }

    async function loadSurvey(id) {
        try {
            const response = await fetch(`/api/survey/${id}`);
            const data = await response.json();
            if (data.code !== 0 || !data.data) {
                window.appNotify(data.message || "记录不存在", "error");
                return;
            }

            resetSurveyExpansion();
            setSurveyText(data.data.content || "");
            surveyActions.style.display = "flex";
            updateSurveyCollapse();
        } catch (error) {
            window.appNotify("读取历史记录失败", "error");
        }
    }

    async function generateSurvey() {
        const topic = topicInput.value.trim();
        const paperIds = selectedPaperIds();

        if (!topic) {
            window.appNotify("请先输入研究主题", "warning");
            return;
        }

        generateButton.disabled = true;
        generateButton.textContent = "正在生成...";
        resetSurveyExpansion();
        setSurveyText("");
        surveyActions.style.display = "none";

        try {
            const response = await fetch("/api/survey/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ topic, paper_ids: paperIds }),
            });

            if (!response.ok || !response.body) {
                throw new Error("流式响应不可用");
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";
            let generatedText = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) {
                    break;
                }

                buffer += decoder.decode(value, { stream: true });
                const events = buffer.split("\n\n");
                buffer = events.pop() || "";

                events.forEach((eventText) => {
                    const line = eventText.trim();
                    if (!line.startsWith("data: ")) {
                        return;
                    }

                    try {
                        const payload = JSON.parse(line.slice(6));
                        if (payload.chunk) {
                            generatedText += payload.chunk;
                            setSurveyText(generatedText);
                        }
                        if (payload.error) {
                            throw new Error(payload.error);
                        }
                    } catch (error) {
                        throw error;
                    }
                });
            }

            surveyActions.style.display = "flex";
            updateSurveyCollapse();
            window.appNotify("综述草稿生成完成", "success");
            loadHistory();
        } catch (error) {
            window.appNotify(error.message || "生成失败，请稍后重试", "error");
        } finally {
            generateButton.textContent = "开始生成综述草稿";
            updateGenerateButton();
        }
    }

    async function recommendTopic() {
        const paperIds = selectedPaperIds();

        if (!paperIds.length) {
            window.appNotify("请先选择参考文献，再让 AI 推荐主题", "warning");
            return;
        }

        const originalText = recommendTopicButton.textContent;
        recommendTopicButton.disabled = true;
        recommendTopicButton.textContent = "生成中...";
        clearTopicRecommendation();

        try {
            const response = await fetch("/api/survey/recommend-topic", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ paper_ids: paperIds }),
            });
            const data = await response.json();

            if (data.code !== 0) {
                window.appNotify(data.message || "主题推荐失败", "error");
                return;
            }

            renderTopicRecommendation(data.data?.topic || "");
            window.appNotify("AI 已生成推荐主题", "success");
        } catch (error) {
            window.appNotify("主题推荐失败，请稍后重试", "error");
        } finally {
            recommendTopicButton.disabled = false;
            recommendTopicButton.textContent = originalText;
        }
    }

    paperCheckboxes?.addEventListener("change", () => {
        clearTopicRecommendation();
        updateGenerateButton();
    });
    topicInput?.addEventListener("input", updateGenerateButton);
    generateButton?.addEventListener("click", generateSurvey);
    recommendTopicButton?.addEventListener("click", recommendTopic);
    topicRecommendation?.addEventListener("click", (event) => {
        const button = event.target.closest(".topic-apply-btn");
        if (!button || !recommendedTopic) {
            return;
        }
        topicInput.value = recommendedTopic;
        updateGenerateButton();
        window.appNotify("已采用推荐主题", "success");
    });
    toggleButton?.addEventListener("click", () => {
        const expanded = !surveyOutputShell?.classList.contains("is-expanded");
        surveyManuallyExpanded = expanded;
        setSurveyExpanded(expanded);
    });
    copyButton?.addEventListener("click", () => window.appCopyText(surveyRawText, "综述内容已复制"));

    historyList?.addEventListener("click", (event) => {
        const item = event.target.closest(".history-item");
        if (item) {
            loadSurvey(item.dataset.id);
        }
    });

    loadPapers();
    loadHistory();
});
