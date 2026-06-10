document.addEventListener("DOMContentLoaded", () => {
    const uploadArea = document.getElementById("chart-upload-area");
    const fileInput = document.getElementById("chart-file-input");
    const analyzeButton = document.getElementById("btn-chart-analyze");
    const resultBox = document.getElementById("chart-result");
    const previewBox = document.getElementById("chart-preview");

    let selectedFile = null;

    function setSelectedFile(file) {
        selectedFile = file || null;
        const text = uploadArea?.querySelector(".upload-text");
        if (text) {
            text.textContent = selectedFile ? `已选择：${selectedFile.name}` : "拖拽图表图片到这里，或点击选择文件";
        }
    }

    async function analyzeSelectedFile() {
        if (!selectedFile) {
            window.appNotify("请先选择图片", "warning");
            return;
        }

        const formData = new FormData();
        formData.append("file", selectedFile);

        analyzeButton.disabled = true;
        analyzeButton.textContent = "解析中...";
        resultBox.textContent = "";
        previewBox.innerHTML = "";

        try {
            const response = await fetch("/api/chart/analyze", {
                method: "POST",
                body: formData,
            });
            const data = await response.json();
            if (data.code !== 0) {
                window.appNotify(data.message || "图表解析失败", "error");
                resultBox.textContent = data.message || "图表解析失败";
                return;
            }

            const result = data.data || {};
            resultBox.innerHTML = `
                <p><strong>图表类型：</strong>${window.appEscapeHtml(result.chart_type || "未识别")}</p>
                <p><strong>总体趋势：</strong>${window.appEscapeHtml(result.trend || "未识别")}</p>
                <p><strong>统计摘要：</strong>${window.appEscapeHtml(JSON.stringify(result.statistics || {}, null, 2))}</p>
                <p><strong>显著性说明：</strong>${window.appEscapeHtml(result.significance || "未提供")}</p>
                <p><strong>分析段落：</strong>${window.appEscapeHtml(result.paragraph || "未提供")}</p>
                <p><strong>关键信息：</strong></p>
                <ul>${(result.key_findings || []).map((item) => `<li>${window.appEscapeHtml(item)}</li>`).join("")}</ul>
            `;

            if (result.image_url) {
                previewBox.innerHTML = `<img src="${window.appEscapeHtml(result.image_url)}" alt="chart preview" style="max-width:100%; border-radius:16px;">`;
            }
            window.appNotify("图表解析完成", "success");
        } catch (error) {
            resultBox.textContent = "图表解析失败，请稍后重试。";
            window.appNotify("图表解析失败，请稍后重试", "error");
        } finally {
            analyzeButton.disabled = false;
            analyzeButton.textContent = "开始解析";
        }
    }

    uploadArea?.addEventListener("click", () => fileInput?.click());
    uploadArea?.addEventListener("dragover", (event) => {
        event.preventDefault();
        uploadArea.classList.add("dragover");
    });
    uploadArea?.addEventListener("dragleave", () => uploadArea.classList.remove("dragover"));
    uploadArea?.addEventListener("drop", (event) => {
        event.preventDefault();
        uploadArea.classList.remove("dragover");
        const file = event.dataTransfer?.files?.[0];
        if (file) {
            setSelectedFile(file);
        }
    });
    fileInput?.addEventListener("change", () => setSelectedFile(fileInput.files?.[0] || null));
    analyzeButton?.addEventListener("click", analyzeSelectedFile);
});
