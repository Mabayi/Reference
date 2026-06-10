document.addEventListener("DOMContentLoaded", async () => {
    const metricsContainer = document.getElementById("home-overview-metrics");
    const statusContainer = document.getElementById("home-overview-status");
    const recentPapersContainer = document.getElementById("home-recent-papers");
    const recentSurveysContainer = document.getElementById("home-recent-surveys");

    function renderMetrics(totalPapers, parsedPapers, surveyCount, systemStatus) {
        const pendingPapers = Math.max(totalPapers - parsedPapers, 0);
        const keyStatus = systemStatus?.is_bound ? "系统 Key 可用" : "系统 Key 未配置";
        const balanceText = systemStatus?.balance?.balance_text || "¥0.00";

        metricsContainer.innerHTML = `
            <div class="home-metric-card">
                <strong>${totalPapers}</strong>
                <span>总文献数</span>
                <small>已入库文献</small>
            </div>
            <div class="home-metric-card">
                <strong>${parsedPapers}</strong>
                <span>已解析</span>
                <small>可直接使用</small>
            </div>
            <div class="home-metric-card">
                <strong>${surveyCount}</strong>
                <span>综述记录</span>
                <small>已保存内容</small>
            </div>
            <div class="home-metric-card">
                <strong>${window.appEscapeHtml(balanceText)}</strong>
                <span>我的额度</span>
                <small>${window.appEscapeHtml(keyStatus)}</small>
            </div>
        `;

        statusContainer.innerHTML = `
            <div class="home-status-item">
                <span>资料</span>
                <p>${parsedPapers} 篇已解析，${pendingPapers} 篇处理中。</p>
            </div>
            <div class="home-status-item">
                <span>综述</span>
                <p>当前共 ${surveyCount} 条记录。</p>
            </div>
            <div class="home-status-item">
                <span>额度</span>
                <p>${window.appEscapeHtml(keyStatus)}，当前额度 ${window.appEscapeHtml(balanceText)}。</p>
            </div>
        `;
    }

    function renderRecentPapers(papers) {
        if (!papers.length) {
            recentPapersContainer.innerHTML = `
                <div class="home-empty">
                    <h4>还没有文献记录</h4>
                    <p>先上传 PDF。</p>
                </div>
            `;
            return;
        }

        recentPapersContainer.innerHTML = papers.slice(0, 5).map((paper) => {
            const title = paper.title || paper.filename || "未命名文献";
            const authors = window.appFormatAuthors(paper.authors);
            const statusText = paper.parse_status === "done" ? "已解析" : paper.parse_status === "failed" ? "失败" : "处理中";
            const target = paper.parse_status === "done" ? `/reader/${paper.id}` : "/papers";
            return `
                <a href="${target}" class="home-list-item">
                    <div class="home-list-main">
                        <strong class="home-list-title">${window.appEscapeHtml(title)}</strong>
                        <p class="home-list-meta">${window.appEscapeHtml(authors)}</p>
                    </div>
                    <div class="home-list-side">
                        <span class="home-list-badge">${window.appEscapeHtml(statusText)}</span>
                        <small>${window.appEscapeHtml(String(paper.year || "-"))}</small>
                    </div>
                </a>
            `;
        }).join("");
    }

    function renderRecentSurveys(surveys) {
        if (!surveys.length) {
            recentSurveysContainer.innerHTML = `
                <div class="home-empty">
                    <h4>还没有综述记录</h4>
                    <p>先选择文献并输入主题。</p>
                </div>
            `;
            return;
        }

        recentSurveysContainer.innerHTML = surveys.slice(0, 5).map((survey) => `
            <a href="/survey" class="home-list-item">
                    <div class="home-list-main">
                        <strong class="home-list-title">${window.appEscapeHtml(survey.topic || "未命名主题")}</strong>
                        <p class="home-list-meta">已保存记录</p>
                    </div>
                <div class="home-list-side">
                    <span class="home-list-badge">综述</span>
                    <small>${window.appEscapeHtml(survey.created_at || "-")}</small>
                </div>
            </a>
        `).join("");
    }

    try {
        const [papersResponse, surveysResponse, deepseekResponse] = await Promise.all([
            fetch("/api/papers"),
            fetch("/api/survey/list"),
            fetch("/api/tokens/deepseek/status"),
        ]);

        const papersData = await papersResponse.json();
        const surveysData = await surveysResponse.json();
        const deepseekData = await deepseekResponse.json();

        const papers = papersData.code === 0 ? (papersData.data || []) : [];
        const surveys = surveysData.code === 0 ? (surveysData.data || []) : [];
        const systemStatus = deepseekData.code === 0 ? (deepseekData.data || {}) : {};
        const parsedPapers = papers.filter((paper) => paper.parse_status === "done").length;

        renderMetrics(papers.length, parsedPapers, surveys.length, systemStatus);
        renderRecentPapers(papers);
        renderRecentSurveys(surveys);
    } catch (error) {
        metricsContainer.innerHTML = `
            <div class="home-metric-card">
                <strong>--</strong>
                <span>数据加载失败</span>
                <small>请刷新页面后重试</small>
            </div>
        `;
        statusContainer.innerHTML = `
            <div class="home-status-item">
                <span>状态</span>
                <p>当前账户概况暂时无法加载，请刷新页面后重试。</p>
            </div>
        `;
        recentPapersContainer.innerHTML = '<div class="home-empty"><h4>加载失败</h4><p>请刷新重试。</p></div>';
        recentSurveysContainer.innerHTML = '<div class="home-empty"><h4>加载失败</h4><p>请刷新重试。</p></div>';
    }
});
