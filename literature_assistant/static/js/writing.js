document.addEventListener("DOMContentLoaded", () => {
    const tabButtons = document.querySelectorAll(".tab-btn");
    const tabContents = document.querySelectorAll(".tab-content");
    const resultBox = document.getElementById("writing-result");
    const wordCount = document.getElementById("word-count");
    const copyButton = document.getElementById("btn-copy-writing");
    const actionButtons = document.querySelectorAll(".writing-generate-btn");

    function switchTab(tabName) {
        tabButtons.forEach((button) => {
            button.classList.toggle("active", button.dataset.tab === tabName);
        });
        tabContents.forEach((content) => {
            content.classList.toggle("active", content.id === `tab-${tabName}`);
        });
    }

    async function generateWriting(action, triggerButton) {
        let endpoint = "";
        let payload = {};

        if (action === "method") {
            const content = document.getElementById("method-content").value.trim();
            if (!content) {
                window.appNotify("请先填写研究内容", "warning");
                return;
            }
            endpoint = "/api/writing/method";
            payload = { content };
        } else if (action === "discussion") {
            const results = document.getElementById("discussion-results").value.trim();
            if (!results) {
                window.appNotify("请先填写研究结果", "warning");
                return;
            }
            endpoint = "/api/writing/discussion";
            payload = { results };
        } else {
            const text = document.getElementById("polish-text").value.trim();
            if (!text) {
                window.appNotify("请先输入待润色文本", "warning");
                return;
            }
            endpoint = "/api/writing/polish";
            payload = { text };
        }

        const originalText = triggerButton.textContent;
        triggerButton.disabled = true;
        triggerButton.textContent = "生成中...";

        try {
            const response = await fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            const data = await response.json();

            if (data.code !== 0) {
                window.appNotify(data.message || "生成失败", "error");
                return;
            }

            const content = data.data?.content || "";
            resultBox.textContent = content;
            wordCount.textContent = `当前字数：${content.length}`;
            window.appNotify("写作结果已生成", "success");
        } catch (error) {
            window.appNotify("生成失败，请稍后重试", "error");
        } finally {
            triggerButton.disabled = false;
            triggerButton.textContent = originalText;
        }
    }

    tabButtons.forEach((button) => {
        button.addEventListener("click", () => switchTab(button.dataset.tab));
    });

    actionButtons.forEach((button) => {
        button.addEventListener("click", () => generateWriting(button.dataset.action, button));
    });

    copyButton?.addEventListener("click", () => {
        window.appCopyText(resultBox.textContent, "写作结果已复制");
    });
});
