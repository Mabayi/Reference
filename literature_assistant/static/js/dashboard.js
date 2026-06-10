document.addEventListener("DOMContentLoaded", async () => {
    const statsContainer = document.getElementById("stats-cards");
    const keywordContainer = document.getElementById("keyword-cloud");
    const trendContainer = document.getElementById("trend-chart");
    const topPapersContainer = document.getElementById("top-papers");

    const escapeHtml = (value) => window.appEscapeHtml(String(value ?? ""));
    const numberValue = (value) => Math.max(0, Number(value || 0));

    function truncateText(value, maxLength = 18) {
        const text = String(value || "");
        return text.length > maxLength ? `${text.slice(0, maxLength - 1)}...` : text;
    }

    function renderStats(stats) {
        const cards = [
            {
                value: stats.total_papers ?? 0,
                label: "总文献数",
                desc: "当前账户已入库文献",
                tone: "blue",
            },
            {
                value: stats.total_surveys ?? 0,
                label: "综述记录",
                desc: "已保存综述草稿",
                tone: "green",
            },
            {
                value: stats.total_experiments ?? 0,
                label: "实验草案",
                desc: "已生成实验方案",
                tone: "amber",
            },
            {
                value: stats.papers_this_month ?? 0,
                label: "本月新增",
                desc: "按入库时间统计",
                tone: "rose",
            },
        ];

        statsContainer.innerHTML = cards.map((card) => `
            <div class="stat-card dashboard-stat-card glass-card" data-tone="${card.tone}">
                <div class="stat-card-top">
                    <span class="stat-dot"></span>
                    <span class="stat-label">${escapeHtml(card.label)}</span>
                </div>
                <div class="stat-number">${escapeHtml(card.value)}</div>
                <div class="stat-desc">${escapeHtml(card.desc)}</div>
            </div>
        `).join("");
    }

    function renderKeywordChart(items) {
        const topItems = (items || [])
            .map((item) => ({ word: String(item.word || "").trim(), count: numberValue(item.count) }))
            .filter((item) => item.word && item.count > 0)
            .slice(0, 12);

        if (!topItems.length) {
            keywordContainer.innerHTML = '<p class="empty-hint">暂无关键词数据，请先上传并解析文献。</p>';
            return;
        }

        const width = 760;
        const rowHeight = 34;
        const height = Math.max(320, 82 + topItems.length * rowHeight);
        const left = 176;
        const right = 66;
        const top = 34;
        const chartWidth = width - left - right;
        const maxCount = Math.max(...topItems.map((item) => item.count), 1);
        keywordContainer.style.height = `${Math.min(height, 460)}px`;

        const gridTicks = [0, 0.25, 0.5, 0.75, 1];
        const bars = topItems.map((item, index) => {
            const y = top + index * rowHeight + 7;
            const barWidth = Math.max(6, (item.count / maxCount) * chartWidth);
            const valueX = Math.min(left + barWidth + 10, width - right + 8);
            const colorClass = index % 4;
            return `
                <g class="keyword-row">
                    <text x="${left - 14}" y="${y + 13}" text-anchor="end" class="dashboard-axis-label">
                        ${escapeHtml(truncateText(item.word))}
                    </text>
                    <rect x="${left}" y="${y}" width="${chartWidth}" height="18" rx="9" class="keyword-bar-bg"></rect>
                    <rect x="${left}" y="${y}" width="${barWidth}" height="18" rx="9" class="keyword-bar keyword-bar-${colorClass}">
                        <title>${escapeHtml(item.word)}：${escapeHtml(item.count)}</title>
                    </rect>
                    <text x="${valueX}" y="${y + 13}" class="dashboard-value-label">${escapeHtml(item.count)}</text>
                </g>
            `;
        }).join("");

        keywordContainer.innerHTML = `
            <svg viewBox="0 0 ${width} ${height}" class="dashboard-svg keyword-svg" role="img" aria-label="关键词频次柱状图">
                ${gridTicks.map((tick) => {
                    const x = left + tick * chartWidth;
                    return `
                        <line x1="${x}" y1="${top - 8}" x2="${x}" y2="${height - 38}" class="dashboard-grid-line"></line>
                        <text x="${x}" y="${height - 16}" text-anchor="middle" class="dashboard-tick-label">${Math.round(tick * maxCount)}</text>
                    `;
                }).join("")}
                ${bars}
            </svg>
        `;
    }

    function renderTrendChart(items) {
        const pointsData = (items || [])
            .map((item) => ({ year: String(item.year || "").trim(), count: numberValue(item.count) }))
            .filter((item) => item.year && item.count >= 0);

        if (!pointsData.length) {
            trendContainer.innerHTML = '<p class="empty-hint">暂无年度分布数据。</p>';
            return;
        }

        const width = 820;
        const height = 360;
        const left = 58;
        const right = 32;
        const top = 30;
        const bottom = 50;
        const chartWidth = width - left - right;
        const chartHeight = height - top - bottom;
        const rawMax = Math.max(...pointsData.map((item) => item.count), 1);
        const maxValue = rawMax <= 5 ? rawMax : Math.ceil(rawMax / 5) * 5;
        const stepX = pointsData.length > 1 ? chartWidth / (pointsData.length - 1) : 0;
        const barWidth = Math.min(48, Math.max(20, chartWidth / Math.max(pointsData.length, 1) * 0.42));
        const labelStep = Math.max(1, Math.ceil(pointsData.length / 8));

        const points = pointsData.map((item, index) => {
            const x = pointsData.length === 1 ? left + chartWidth / 2 : left + index * stepX;
            const y = top + chartHeight - (item.count / maxValue) * chartHeight;
            return { ...item, x, y };
        });

        const baseline = top + chartHeight;
        const polyline = points.map((point) => `${point.x},${point.y}`).join(" ");
        const areaPoints = `${points[0].x},${baseline} ${polyline} ${points[points.length - 1].x},${baseline}`;
        const gridLines = Array.from({ length: 5 }, (_, index) => {
            const value = Math.round((maxValue / 4) * index);
            const y = baseline - (value / maxValue) * chartHeight;
            return { value, y };
        });

        trendContainer.style.height = "380px";
        trendContainer.innerHTML = `
            <svg viewBox="0 0 ${width} ${height}" class="dashboard-svg trend-svg" role="img" aria-label="年度文献分布趋势图">
                ${gridLines.map((line) => `
                    <line x1="${left}" y1="${line.y}" x2="${width - right}" y2="${line.y}" class="dashboard-grid-line"></line>
                    <text x="${left - 14}" y="${line.y + 4}" text-anchor="end" class="dashboard-tick-label">${escapeHtml(line.value)}</text>
                `).join("")}
                <line x1="${left}" y1="${top}" x2="${left}" y2="${baseline}" class="dashboard-axis-line"></line>
                <line x1="${left}" y1="${baseline}" x2="${width - right}" y2="${baseline}" class="dashboard-axis-line"></line>
                ${points.map((point) => {
                    const barHeight = baseline - point.y;
                    return `
                        <rect x="${point.x - barWidth / 2}" y="${point.y}" width="${barWidth}" height="${barHeight}" rx="8" class="trend-bar">
                            <title>${escapeHtml(point.year)}：${escapeHtml(point.count)} 篇</title>
                        </rect>
                    `;
                }).join("")}
                <polygon points="${areaPoints}" class="trend-area"></polygon>
                <polyline points="${polyline}" class="trend-line"></polyline>
                ${points.map((point, index) => `
                    <circle cx="${point.x}" cy="${point.y}" r="5.5" class="trend-point">
                        <title>${escapeHtml(point.year)}：${escapeHtml(point.count)} 篇</title>
                    </circle>
                    <text x="${point.x}" y="${point.y - 12}" text-anchor="middle" class="dashboard-value-label">${escapeHtml(point.count)}</text>
                    ${(index % labelStep === 0 || index === points.length - 1) ? `<text x="${point.x}" y="${baseline + 28}" text-anchor="middle" class="dashboard-axis-label">${escapeHtml(point.year)}</text>` : ""}
                `).join("")}
            </svg>
        `;
    }

    function renderTopPapers(items) {
        const papers = items || [];
        if (!papers.length) {
            topPapersContainer.innerHTML = '<p class="empty-hint">暂无已入库文献。</p>';
            return;
        }

        topPapersContainer.innerHTML = papers.map((paper, index) => `
            <div class="top-paper-item glass-card">
                <div class="top-paper-rank">${index + 1}</div>
                <div class="top-paper-meta">
                    <strong>${escapeHtml(paper.title || "未命名文献")}</strong>
                    <p>${escapeHtml(window.appFormatAuthors(paper.authors))}</p>
                </div>
                <div class="top-paper-year">${escapeHtml(paper.year || "-")}</div>
            </div>
        `).join("");
    }

    try {
        const [statsResponse, keywordResponse, trendResponse, papersResponse] = await Promise.all([
            fetch("/api/dashboard/stats"),
            fetch("/api/dashboard/keywords"),
            fetch("/api/dashboard/yearly-trend"),
            fetch("/api/dashboard/top-papers"),
        ]);

        const statsData = await statsResponse.json();
        const keywordData = await keywordResponse.json();
        const trendData = await trendResponse.json();
        const paperData = await papersResponse.json();

        if (statsData.code === 0) {
            renderStats(statsData.data || {});
        }
        if (keywordData.code === 0) {
            renderKeywordChart(keywordData.data || []);
        }
        if (trendData.code === 0) {
            renderTrendChart(trendData.data || []);
        }
        if (paperData.code === 0) {
            renderTopPapers(paperData.data || []);
        }
    } catch (error) {
        window.appNotify("趋势页部分数据加载失败", "warning");
    }
});
