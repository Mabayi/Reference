document.addEventListener("DOMContentLoaded", () => {
    const generateButton = document.getElementById("btn-codegen");
    const codeResult = document.getElementById("code-result");
    const languageLabel = document.getElementById("code-lang-label");
    const copyButton = document.getElementById("btn-copy-code");

    generateButton?.addEventListener("click", async () => {
        const summary = document.getElementById("exp-summary").value.trim();
        const language = document.querySelector('input[name="language"]:checked')?.value || "python";

        if (!summary) {
            window.appNotify("请先描述分析任务", "warning");
            return;
        }

        generateButton.disabled = true;
        generateButton.textContent = "生成中...";

        try {
            const response = await fetch("/api/codegen/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ experiment_summary: summary, language }),
            });
            const data = await response.json();

            if (data.code !== 0) {
                window.appNotify(data.message || "生成失败", "error");
                return;
            }

            codeResult.textContent = data.data?.code || "";
            languageLabel.textContent = data.data?.language === "r" ? "R" : "Python";
            window.appNotify("代码草稿已生成", "success");
        } catch (error) {
            window.appNotify("生成失败，请稍后重试", "error");
        } finally {
            generateButton.disabled = false;
            generateButton.textContent = "生成代码草稿";
        }
    });

    copyButton?.addEventListener("click", () => {
        window.appCopyText(codeResult.textContent, "代码已复制");
    });
});
