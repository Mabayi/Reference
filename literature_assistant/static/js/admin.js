document.addEventListener("DOMContentLoaded", () => {
    const overview = document.getElementById("admin-overview");
    const userList = document.getElementById("admin-user-list");
    const ticketList = document.getElementById("admin-ticket-list");
    const tokenUsers = document.getElementById("admin-token-users");
    const tokenLogs = document.getElementById("admin-token-logs");
    const statusFilter = document.getElementById("ticket-status-filter");
    const refreshUsageButton = document.getElementById("btn-refresh-usage");
    const usageSummary = document.getElementById("usage-summary");
    const usageRecentConsumed = document.getElementById("usage-recent-consumed");
    const usageTokenTrend = document.getElementById("usage-token-trend");
    const usageUserGrowth = document.getElementById("usage-user-growth");
    const usageTokenActions = document.getElementById("usage-token-actions");
    const usageTopUsers = document.getElementById("usage-top-users");
    const usageTicketStatus = document.getElementById("usage-ticket-status");
    const usageTicketInsight = document.getElementById("usage-ticket-insight");
    const tabButtons = document.querySelectorAll(".admin-console-nav .admin-nav-item, .admin-tabs .tab-btn");
    const panels = document.querySelectorAll(".admin-panel");

    function formatNumber(value) {
        return Number(value || 0).toLocaleString("zh-CN");
    }

    function shortDate(value) {
        const parts = String(value || "").split("-");
        if (parts.length !== 3) {
            return window.appEscapeHtml(value || "-");
        }
        return `${Number(parts[1])}/${Number(parts[2])}`;
    }

    function renderEmpty(container, text) {
        if (!container) {
            return;
        }
        container.innerHTML = `<p class="empty-hint">${window.appEscapeHtml(text || "暂无数据。")}</p>`;
    }

    function hasPositiveValue(items, key = "value") {
        return (items || []).some((item) => Number(item[key] || 0) > 0);
    }

    function renderLineChart(container, items, emptyText) {
        if (!container) {
            return;
        }
        const rows = items || [];
        if (!rows.length || !hasPositiveValue(rows)) {
            renderEmpty(container, emptyText);
            return;
        }

        const width = 760;
        const height = 260;
        const left = 54;
        const right = 24;
        const top = 26;
        const bottom = 44;
        const chartWidth = width - left - right;
        const chartHeight = height - top - bottom;
        const maxValue = Math.max(...rows.map((item) => Number(item.value || 0)), 1);
        const stepX = rows.length > 1 ? chartWidth / (rows.length - 1) : 0;
        const baseline = top + chartHeight;
        const points = rows.map((item, index) => {
            const value = Number(item.value || 0);
            const x = rows.length === 1 ? left + chartWidth / 2 : left + index * stepX;
            const y = baseline - (value / maxValue) * chartHeight;
            return { x, y, value, label: item.date || item.label || "" };
        });
        const linePoints = points.map((point) => `${point.x.toFixed(2)},${point.y.toFixed(2)}`).join(" ");
        const areaPoints = `${left},${baseline} ${linePoints} ${left + chartWidth},${baseline}`;
        const gridLines = [0, 0.25, 0.5, 0.75, 1].map((ratio) => {
            const y = baseline - ratio * chartHeight;
            const value = Math.round(maxValue * ratio);
            return `
                <line x1="${left}" y1="${y}" x2="${left + chartWidth}" y2="${y}" class="admin-chart-grid"></line>
                <text x="${left - 12}" y="${y + 4}" text-anchor="end" class="admin-chart-axis">${formatNumber(value)}</text>
            `;
        }).join("");
        const markers = points.map((point) => `
            <g>
                <circle cx="${point.x}" cy="${point.y}" r="5" class="admin-chart-dot"></circle>
                <title>${window.appEscapeHtml(point.label)}：${formatNumber(point.value)}</title>
            </g>
        `).join("");
        const labels = points.map((point, index) => {
            if (rows.length > 6 && index % 2 === 1 && index !== rows.length - 1) {
                return "";
            }
            return `<text x="${point.x}" y="${height - 15}" text-anchor="middle" class="admin-chart-axis">${shortDate(point.label)}</text>`;
        }).join("");

        container.innerHTML = `
            <svg viewBox="0 0 ${width} ${height}" class="admin-usage-svg" role="img" aria-label="DeepSeek API 用量趋势">
                ${gridLines}
                <polygon points="${areaPoints}" class="admin-chart-area"></polygon>
                <polyline points="${linePoints}" class="admin-chart-line"></polyline>
                ${markers}
                ${labels}
            </svg>
        `;
    }

    function renderColumnChart(container, items, emptyText) {
        if (!container) {
            return;
        }
        const rows = items || [];
        if (!rows.length || !hasPositiveValue(rows)) {
            renderEmpty(container, emptyText);
            return;
        }

        const width = 460;
        const height = 230;
        const left = 34;
        const right = 18;
        const top = 22;
        const bottom = 38;
        const chartWidth = width - left - right;
        const chartHeight = height - top - bottom;
        const maxValue = Math.max(...rows.map((item) => Number(item.value || 0)), 1);
        const gap = 10;
        const barWidth = Math.max(18, (chartWidth - gap * (rows.length - 1)) / Math.max(rows.length, 1));
        const baseline = top + chartHeight;
        const bars = rows.map((item, index) => {
            const value = Number(item.value || 0);
            const barHeight = Math.max(value > 0 ? 6 : 0, (value / maxValue) * chartHeight);
            const x = left + index * (barWidth + gap);
            const y = baseline - barHeight;
            return `
                <g>
                    <rect x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" rx="7" class="admin-chart-bar"></rect>
                    <text x="${x + barWidth / 2}" y="${height - 14}" text-anchor="middle" class="admin-chart-axis">${shortDate(item.date || item.label)}</text>
                    <title>${window.appEscapeHtml(item.date || item.label || "-")}：${formatNumber(value)}</title>
                </g>
            `;
        }).join("");

        container.innerHTML = `
            <svg viewBox="0 0 ${width} ${height}" class="admin-usage-svg" role="img" aria-label="新增用户柱状图">
                <line x1="${left}" y1="${baseline}" x2="${left + chartWidth}" y2="${baseline}" class="admin-chart-grid"></line>
                ${bars}
            </svg>
        `;
    }

    function renderDistribution(container, items, options = {}) {
        if (!container) {
            return;
        }
        const rows = (items || []).filter((item) => Number(item.value || item.count || 0) > 0);
        if (!rows.length) {
            renderEmpty(container, options.emptyText || "暂无分布数据。");
            return;
        }
        const maxValue = Math.max(...rows.map((item) => Number(item.value || item.count || 0)), 1);
        container.innerHTML = `
            <div class="admin-distribution-list">
                ${rows.map((item) => {
                    const value = Number(item.value || item.count || 0);
                    const width = Math.max(5, (value / maxValue) * 100);
                    return `
                        <div class="admin-distribution-row">
                            <span>${window.appEscapeHtml(item.label || item.action || "-")}</span>
                            <div class="admin-distribution-track">
                                <i style="width:${width}%"></i>
                            </div>
                            <strong>${formatNumber(value)}</strong>
                        </div>
                    `;
                }).join("")}
            </div>
        `;
    }

    function renderTokenActions(container, items) {
        const rows = (items || []).map((item) => ({
            label: item.label || item.action || "-",
            value: Number(item.count || 0),
            amount: Number(item.amount || 0),
        })).filter((item) => item.value > 0);
        if (!container) {
            return;
        }
        if (!rows.length) {
            renderEmpty(container, "暂无 API 用量记录。");
            return;
        }
        const maxValue = Math.max(...rows.map((item) => item.value), 1);
        container.innerHTML = `
            <div class="admin-distribution-list">
                ${rows.map((item) => `
                    <div class="admin-distribution-row stacked">
                        <span>${window.appEscapeHtml(item.label)}</span>
                        <div class="admin-distribution-track">
                            <i style="width:${Math.max(5, (item.value / maxValue) * 100)}%"></i>
                        </div>
                        <strong>${formatNumber(item.value)} 次</strong>
                        <small>${formatNumber(item.amount)} token</small>
                    </div>
                `).join("")}
            </div>
        `;
    }

    function renderTopUsers(container, users) {
        if (!container) {
            return;
        }
        const rows = (users || []).map((user) => {
            const consumed = Number(user.consumed || 0);
            const activity = Number(user.activity_count || 0);
            return {
                ...user,
                consumed,
                activity,
                metric: consumed > 0 ? consumed : activity,
            };
        }).filter((user) => user.metric > 0);

        if (!rows.length) {
            renderEmpty(container, "暂无用户使用记录。");
            return;
        }

        const maxValue = Math.max(...rows.map((user) => user.metric), 1);
        container.innerHTML = `
            <div class="admin-top-users">
                ${rows.map((user, index) => {
                    const width = Math.max(6, (user.metric / maxValue) * 100);
                    return `
                        <div class="admin-top-user-row">
                            <span class="admin-rank">${index + 1}</span>
                            <div class="admin-top-user-main">
                                <strong>${window.appEscapeHtml(user.username || "-")}</strong>
                        <small>${formatNumber(user.consumed)} API token · ${formatNumber(user.activity)} 次记录 · ${window.appEscapeHtml(user.deepseek_balance_text || "未绑定")}</small>
                            </div>
                            <div class="admin-top-user-bar">
                                <i style="width:${width}%"></i>
                            </div>
                            <b>${formatNumber(user.metric)}</b>
                        </div>
                    `;
                }).join("")}
            </div>
        `;
    }

    function renderTicketInsight(container, sentiments, categories) {
        if (!container) {
            return;
        }
        const hasSentiments = hasPositiveValue(sentiments || []);
        const hasCategories = hasPositiveValue(categories || []);
        if (!hasSentiments && !hasCategories) {
            renderEmpty(container, "暂无客服分类数据。");
            return;
        }

        const listHtml = (title, rows) => {
            const cleanRows = (rows || []).filter((item) => Number(item.value || 0) > 0);
            const maxValue = Math.max(...cleanRows.map((item) => Number(item.value || 0)), 1);
            return `
                <div class="admin-insight-group">
                    <h4>${window.appEscapeHtml(title)}</h4>
                    ${cleanRows.map((item) => {
                        const value = Number(item.value || 0);
                        return `
                            <div class="admin-distribution-row">
                                <span>${window.appEscapeHtml(item.label || "-")}</span>
                                <div class="admin-distribution-track">
                                    <i style="width:${Math.max(5, (value / maxValue) * 100)}%"></i>
                                </div>
                                <strong>${formatNumber(value)}</strong>
                            </div>
                        `;
                    }).join("") || '<p class="empty-hint">暂无数据。</p>'}
                </div>
            `;
        };

        container.innerHTML = `
            <div class="admin-ticket-insight-grid">
                ${listHtml("情绪", sentiments || [])}
                ${listHtml("分类", categories || [])}
            </div>
        `;
    }

    function statusText(status) {
        const map = {
            open: "待处理",
            in_progress: "处理中",
            resolved: "已解决",
            closed: "已关闭",
        };
        return map[status] || status || "-";
    }

    function renderOverview(data) {
        const tickets = data.tickets || {};
        const feedback = data.feedback || {};
        const cards = [
            { label: "用户数", value: data.total_users || 0 },
            { label: "待处理工单", value: tickets.open || 0 },
            { label: "AI 回复有效", value: feedback.helpful || 0 },
            { label: "AI 回复无效", value: feedback.not_helpful || 0 },
            { label: "API 停用", value: data.disabled_tokens || 0 },
        ];
        overview.innerHTML = cards.map((card) => `
            <div class="admin-stat glass-card">
                <span>${window.appEscapeHtml(card.label)}</span>
                <strong>${window.appEscapeHtml(card.value)}</strong>
            </div>
        `).join("");
    }

    async function loadOverview() {
        const response = await fetch("/api/admin/overview");
        const data = await response.json();
        if (data.code === 0) {
            renderOverview(data.data || {});
        }
    }

    function renderUsage(data) {
        const summary = data.summary || {};
        if (usageSummary) {
            const summaryCards = [
                { label: "活跃用户", value: summary.active_users || 0 },
                { label: "已绑 Key", value: summary.bound_key_count || 0 },
                { label: "Key 可用", value: summary.available_key_count || 0 },
                { label: "API 停用", value: summary.disabled_count || 0 },
                { label: "用量记录", value: summary.token_log_count || 0 },
                { label: "工单数量", value: summary.ticket_count || 0 },
            ];
            usageSummary.innerHTML = summaryCards.map((card) => `
                <div class="admin-usage-summary-card">
                    <span>${window.appEscapeHtml(card.label)}</span>
                    <strong>${formatNumber(card.value)}</strong>
                </div>
            `).join("");
        }
        if (usageRecentConsumed) {
            usageRecentConsumed.textContent = `${formatNumber(summary.recent_consumed || 0)} token`;
        }
        renderLineChart(usageTokenTrend, data.token_consumption_daily || [], "最近 7 天暂无 API 用量。");
        renderColumnChart(usageUserGrowth, data.new_users_daily || [], "最近 7 天暂无新增用户。");
        renderTokenActions(usageTokenActions, data.token_actions || []);
        renderTopUsers(usageTopUsers, data.top_users || []);
        renderDistribution(usageTicketStatus, data.ticket_status || [], { emptyText: "暂无工单状态数据。" });
        renderTicketInsight(usageTicketInsight, data.ticket_sentiments || [], data.ticket_categories || []);
    }

    async function loadUsage() {
        if (refreshUsageButton) {
            refreshUsageButton.disabled = true;
            refreshUsageButton.textContent = "刷新中...";
        }
        try {
            const response = await fetch("/api/admin/usage");
            const data = await response.json();
            if (data.code === 0) {
                renderUsage(data.data || {});
            } else {
                renderEmpty(usageTokenTrend, data.message || "统计数据加载失败。");
            }
        } finally {
            if (refreshUsageButton) {
                refreshUsageButton.disabled = false;
                refreshUsageButton.textContent = "刷新数据";
            }
        }
    }

    function renderTickets(tickets) {
        if (!tickets.length) {
            ticketList.innerHTML = '<p class="empty-hint">当前没有工单。</p>';
            return;
        }

        const feedbackText = {
            helpful: "有效",
            not_helpful: "无效",
        };

        ticketList.innerHTML = tickets.map((ticket) => `
            <article class="admin-ticket-card" data-id="${ticket.id}">
                <div class="admin-ticket-main">
                    <div>
                        <div class="ticket-title-row">
                            <strong>#${window.appEscapeHtml(ticket.id)} ${window.appEscapeHtml(ticket.subject || "未命名问题")}</strong>
                            <span class="status-pill" data-status="${window.appEscapeHtml(ticket.status || "open")}">${statusText(ticket.status)}</span>
                        </div>
                        <p class="ticket-user">${window.appEscapeHtml(ticket.username || "-")} · ${window.appEscapeHtml(ticket.email || "-")} · ${window.appEscapeHtml(ticket.created_at || "-")}</p>
                        <div class="ticket-meta-row">
                            <span>来源：${ticket.source === "ai" ? "AI 咨询" : "人工工单"}</span>
                            <span>分类：${window.appEscapeHtml(ticket.category || "其他")}</span>
                            <span>情绪：${window.appEscapeHtml(ticket.sentiment || "中性")} ${window.appEscapeHtml(ticket.sentiment_score || 2)}/5</span>
                            <span>优先级：${window.appEscapeHtml(ticket.priority || "普通")}</span>
                            ${ticket.feedback ? `<span>用户反馈：${window.appEscapeHtml(feedbackText[ticket.feedback] || ticket.feedback)}</span>` : ""}
                        </div>
                        <p class="ticket-message">${window.appEscapeHtml(ticket.message || "")}</p>
                        ${ticket.faq_answer ? `<p class="ticket-faq-answer">固定解答：${window.appEscapeHtml(ticket.faq_answer)}</p>` : ""}
                        ${ticket.ai_reply ? `<p class="ticket-ai-reply">AI 回复：${window.appEscapeHtml(ticket.ai_reply)}</p>` : ""}
                        ${ticket.ai_summary ? `<p class="ticket-ai-summary">AI 摘要：${window.appEscapeHtml(ticket.ai_summary)}</p>` : ""}
                        ${ticket.feedback_note ? `<p class="ticket-feedback-note">反馈备注：${window.appEscapeHtml(ticket.feedback_note)}</p>` : ""}
                        ${ticket.admin_reply ? `<div class="ticket-reply"><strong>已回复</strong><p>${window.appEscapeHtml(ticket.admin_reply)}</p></div>` : ""}
                    </div>
                    <div class="admin-ticket-actions">
                        <select class="ticket-status-select">
                            ${["open", "in_progress", "resolved", "closed"].map((status) => `
                                <option value="${status}" ${ticket.status === status ? "selected" : ""}>${statusText(status)}</option>
                            `).join("")}
                        </select>
                        <textarea class="ticket-reply-input" rows="3" placeholder="输入客服回复">${window.appEscapeHtml(ticket.admin_reply || "")}</textarea>
                        <button class="btn-primary btn-ticket-reply" type="button">保存回复</button>
                    </div>
                </div>
            </article>
        `).join("");
    }

    async function loadTickets() {
        const status = statusFilter?.value || "all";
        const response = await fetch(`/api/admin/tickets?status=${encodeURIComponent(status)}`);
        const data = await response.json();
        if (data.code === 0) {
            renderTickets(data.data || []);
        }
    }

    function renderUserList(users) {
        if (!users.length) {
            userList.innerHTML = '<p class="empty-hint">暂无用户。</p>';
            return;
        }

        userList.innerHTML = `
            <div class="admin-user-grid">
                ${users.map((user) => {
                    const disabled = Boolean(Number(user.is_disabled || 0));
                    return `
                        <article class="admin-user-item">
                            <div class="admin-user-main">
                                <span class="admin-user-avatar">${window.appEscapeHtml(String(user.username || "-").slice(0, 1).toUpperCase())}</span>
                                <div>
                                    <div class="admin-user-title">
                                        <strong>${window.appEscapeHtml(user.username || "-")}</strong>
                                        ${Number(user.is_admin || 0) ? '<span class="status-pill" data-status="in_progress">管理员</span>' : '<span class="status-pill" data-status="resolved">普通用户</span>'}
                                        <span class="status-pill" data-status="${disabled ? "closed" : "resolved"}">${disabled ? "API 停用" : "API 正常"}</span>
                                        <span class="status-pill" data-status="${Number(user.deepseek_is_available || 0) ? "resolved" : "in_progress"}">${user.deepseek_is_bound ? (Number(user.deepseek_is_available || 0) ? "Key 可用" : "Key 不可用") : "未绑定 Key"}</span>
                                    </div>
                                    <p>${window.appEscapeHtml(user.email || "-")}</p>
                                </div>
                            </div>
                            <div class="admin-user-metrics">
                                <span><small>DeepSeek 余额</small><strong>${window.appEscapeHtml(user.deepseek_balance_text || "未同步")}</strong></span>
                                <span><small>绑定 Key</small><strong>${window.appEscapeHtml(user.deepseek_key_mask || "未绑定")}</strong></span>
                                <span><small>可用性</small><strong>${Number(user.deepseek_is_available || 0) ? "可用" : "未确认"}</strong></span>
                            </div>
                            <div class="admin-user-foot">
                                <span>注册：${window.appEscapeHtml(user.created_at || "-")}</span>
                                <span>最后登录：${window.appEscapeHtml(user.last_login || "未记录")}</span>
                                <button class="btn-secondary btn-toggle-token" type="button" data-user-id="${user.user_id}" data-disabled="${disabled ? "0" : "1"}">
                                    ${disabled ? "恢复 API" : "停用 API"}
                                </button>
                            </div>
                        </article>
                    `;
                }).join("")}
            </div>
        `;
    }

    function renderTokenUsers(users) {
        if (!users.length) {
            tokenUsers.innerHTML = '<p class="empty-hint">暂无用户。</p>';
            return;
        }

        tokenUsers.innerHTML = `
            <div class="paper-table">
                <table class="logs-table admin-table">
                    <thead>
                        <tr>
                            <th>用户</th>
                            <th>邮箱</th>
                            <th>DeepSeek 余额</th>
                            <th>绑定 Key</th>
                            <th>Key 状态</th>
                            <th>状态</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${users.map((user) => {
                            const disabled = Boolean(Number(user.is_disabled || 0));
                            return `
                                <tr>
                                    <td>${window.appEscapeHtml(user.username || "-")}${Number(user.is_admin || 0) ? " · 管理员" : ""}</td>
                                    <td>${window.appEscapeHtml(user.email || "-")}</td>
                                    <td>${window.appEscapeHtml(user.deepseek_balance_text || "未同步")}</td>
                                    <td>${window.appEscapeHtml(user.deepseek_key_mask || "未绑定")}</td>
                                    <td><span class="status-pill" data-status="${Number(user.deepseek_is_available || 0) ? "resolved" : "in_progress"}">${user.deepseek_is_bound ? (Number(user.deepseek_is_available || 0) ? "可用" : "不可用") : "未绑定"}</span></td>
                                    <td><span class="status-pill" data-status="${disabled ? "closed" : "resolved"}">${disabled ? "API 已停用" : "API 正常"}</span></td>
                                    <td>
                                        <button class="btn-secondary btn-toggle-token" data-user-id="${user.user_id}" data-disabled="${disabled ? "0" : "1"}">
                                            ${disabled ? "恢复 API" : "停用 API"}
                                        </button>
                                    </td>
                                </tr>
                            `;
                        }).join("")}
                    </tbody>
                </table>
            </div>
        `;
    }

    async function loadTokenUsers() {
        const response = await fetch("/api/admin/tokens/users");
        const data = await response.json();
        if (data.code === 0) {
            const users = data.data || [];
            renderUserList(users);
            renderTokenUsers(users);
        }
    }

    function renderTokenLogs(logs) {
        if (!logs.length) {
            tokenLogs.innerHTML = '<p class="empty-hint">暂无 API 用量记录。</p>';
            return;
        }

        tokenLogs.innerHTML = `
            <div class="paper-table">
                <table class="logs-table admin-table">
                    <thead>
                        <tr>
                            <th>时间</th>
                            <th>用户</th>
                            <th>类型</th>
                            <th>数量</th>
                            <th>说明</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${logs.map((log) => {
                            const amount = Number(log.amount || 0);
                            const amountClass = amount >= 0 ? "log-add" : "log-consume";
                            return `
                                <tr>
                                    <td>${window.appEscapeHtml(log.created_at || "-")}</td>
                                    <td>${window.appEscapeHtml(log.username || "-")}</td>
                                    <td>${window.appEscapeHtml(log.action || "-")}</td>
                                    <td class="${amountClass}">${amount > 0 ? `+${amount}` : amount}</td>
                                    <td>${window.appEscapeHtml(log.description || "-")}</td>
                                </tr>
                            `;
                        }).join("")}
                    </tbody>
                </table>
            </div>
        `;
    }

    async function loadTokenLogs() {
        const response = await fetch("/api/admin/tokens/logs");
        const data = await response.json();
        if (data.code === 0) {
            renderTokenLogs(data.data || []);
        }
    }

    tabButtons.forEach((button) => {
        button.addEventListener("click", () => {
            tabButtons.forEach((item) => item.classList.toggle("active", item === button));
            panels.forEach((panel) => panel.classList.toggle("active", panel.id === `admin-tab-${button.dataset.adminTab}`));
        });
    });

    statusFilter?.addEventListener("change", loadTickets);

    ticketList?.addEventListener("change", async (event) => {
        const select = event.target.closest(".ticket-status-select");
        if (!select) {
            return;
        }
        const card = select.closest(".admin-ticket-card");
        const response = await fetch(`/api/admin/tickets/${card.dataset.id}/status`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: select.value }),
        });
        const data = await response.json();
        window.appNotify(data.message || "状态已更新", data.code === 0 ? "success" : "error");
        await Promise.all([loadTickets(), loadOverview(), loadUsage()]);
    });

    ticketList?.addEventListener("click", async (event) => {
        const button = event.target.closest(".btn-ticket-reply");
        if (!button) {
            return;
        }
        const card = button.closest(".admin-ticket-card");
        const reply = card.querySelector(".ticket-reply-input").value.trim();
        const status = card.querySelector(".ticket-status-select").value || "resolved";
        if (!reply) {
            window.appNotify("请填写回复内容", "warning");
            return;
        }
        button.disabled = true;
        button.textContent = "保存中...";
        try {
            const response = await fetch(`/api/admin/tickets/${card.dataset.id}/reply`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ reply, status }),
            });
            const data = await response.json();
            window.appNotify(data.message || "已保存", data.code === 0 ? "success" : "error");
            await Promise.all([loadTickets(), loadOverview(), loadUsage()]);
        } finally {
            button.disabled = false;
            button.textContent = "保存回复";
        }
    });

    async function handleToggleToken(event) {
        const button = event.target.closest(".btn-toggle-token");
        if (!button) {
            return;
        }
        const disabled = button.dataset.disabled === "1";
        const confirmed = await window.appConfirm(disabled ? "确认停用该用户 API 使用？" : "确认恢复该用户 API 使用？", {
            message: disabled ? "停用后该用户不能绑定 Key 或继续调用系统内 AI 功能。" : "恢复后该用户可继续使用已绑定的 DeepSeek Key。",
            confirmText: disabled ? "停用" : "恢复",
        });
        if (!confirmed) {
            return;
        }
        const response = await fetch(`/api/admin/tokens/users/${button.dataset.userId}/disabled`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ disabled }),
        });
        const data = await response.json();
        window.appNotify(data.message || "API 状态已更新", data.code === 0 ? "success" : "error");
        await Promise.all([loadTokenUsers(), loadTokenLogs(), loadOverview(), loadUsage()]);
    }

    tokenUsers?.addEventListener("click", handleToggleToken);
    userList?.addEventListener("click", handleToggleToken);
    refreshUsageButton?.addEventListener("click", loadUsage);

    Promise.all([loadOverview(), loadUsage(), loadTickets(), loadTokenUsers(), loadTokenLogs()]).catch(() => {
        window.appNotify("管理后台部分数据加载失败", "warning");
    });
});
