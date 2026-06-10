document.addEventListener("DOMContentLoaded", () => {
    const bindButton = document.getElementById("btn-bind-key");
    const refreshButton = document.getElementById("btn-refresh-deepseek");
    const removeButton = document.getElementById("btn-remove-key");
    const apiKeyInput = document.getElementById("deepseek-api-key");
    const messageBox = document.getElementById("deepseek-msg");
    const detailBox = document.getElementById("deepseek-account-detail");

    function setMessage(message, ok = true) {
        if (!messageBox) {
            return;
        }
        messageBox.textContent = message || "";
        messageBox.className = ok ? "msg msg-success" : "msg msg-error";
    }

    function moneyText(value, currency) {
        const number = Number(value || 0);
        if (Number.isNaN(number)) {
            return `${window.appEscapeHtml(value || "0")} ${window.appEscapeHtml(currency || "")}`;
        }
        return `${number.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 6 })} ${window.appEscapeHtml(currency || "")}`;
    }

    function renderDeepSeekAccount(account) {
        const balanceElement = document.getElementById("deepseek-balance");
        const statusElement = document.getElementById("deepseek-key-status");
        if (!account || !account.is_bound) {
            balanceElement.textContent = "-";
            statusElement.textContent = "未绑定";
            detailBox.innerHTML = '<p class="empty-hint">还没有绑定 DeepSeek API Key。请先在官方平台创建密钥，然后在这里绑定验证。</p>';
            refreshButton.disabled = true;
            removeButton.disabled = true;
            return;
        }

        const balanceInfos = account.balance_infos || [];
        const primaryBalance = balanceInfos[0] || {};
        balanceElement.textContent = primaryBalance.total_balance
            ? moneyText(primaryBalance.total_balance, primaryBalance.currency)
            : "-";
        statusElement.textContent = Number(account.is_available || 0) ? "可用" : "不可用";
        refreshButton.disabled = false;
        removeButton.disabled = false;

        detailBox.innerHTML = `
            <div class="deepseek-key-card">
                <div>
                    <span>已绑定 Key</span>
                    <strong>${window.appEscapeHtml(account.key_mask || "-")}</strong>
                </div>
                <div>
                    <span>最近校验</span>
                    <strong>${window.appEscapeHtml(account.checked_at || "未记录")}</strong>
                </div>
            </div>
            <div class="deepseek-balance-list">
                ${balanceInfos.length ? balanceInfos.map((item) => `
                    <div class="deepseek-balance-row">
                        <span>${window.appEscapeHtml(item.currency || "-")}</span>
                        <strong>${moneyText(item.total_balance, item.currency)}</strong>
                        <small>充值 ${moneyText(item.topped_up_balance, item.currency)} · 赠送 ${moneyText(item.granted_balance, item.currency)}</small>
                    </div>
                `).join("") : '<p class="empty-hint">DeepSeek 未返回余额明细。</p>'}
            </div>
        `;
    }

    async function loadDeepSeekStatus() {
        const response = await fetch("/api/tokens/deepseek/status");
        const data = await response.json();
        if (data.code === 0) {
            renderDeepSeekAccount(data.data || {});
        } else {
            setMessage(data.message || "DeepSeek 账户状态加载失败", false);
        }
    }

    async function loadStats() {
        const response = await fetch("/api/tokens/stats");
        const data = await response.json();
        if (data.code === 0) {
            document.getElementById("today-cost").textContent = Number(data.data.today || 0).toLocaleString();
            document.getElementById("week-cost").textContent = Number(data.data.week || 0).toLocaleString();
        }
    }

    async function loadLogs() {
        const container = document.getElementById("token-logs");
        const response = await fetch("/api/tokens/logs");
        const data = await response.json();
        const logs = data.data || [];

        if (!logs.length) {
            container.innerHTML = '<p class="empty-hint">近 7 天暂无系统用量记录。</p>';
            return;
        }

        container.innerHTML = `
            <div class="paper-table">
                <table class="logs-table">
                    <thead>
                        <tr>
                            <th>时间</th>
                            <th>类型</th>
                            <th>数量</th>
                            <th>说明</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${logs.map((log) => {
                            const amount = Number(log.amount || 0);
                            const amountClass = amount >= 0 ? "log-add" : "log-consume";
                            const amountText = amount > 0 ? `+${amount}` : `${amount}`;
                            return `
                                <tr>
                                    <td>${window.appEscapeHtml(log.created_at)}</td>
                                    <td>${window.appEscapeHtml(log.action)}</td>
                                    <td class="${amountClass}">${window.appEscapeHtml(amountText)}</td>
                                    <td>${window.appEscapeHtml(log.description || "-")}</td>
                                </tr>
                            `;
                        }).join("")}
                    </tbody>
                </table>
            </div>
        `;
    }

    bindButton?.addEventListener("click", async () => {
        const apiKey = apiKeyInput.value.trim();
        if (!apiKey) {
            window.appNotify("请输入 DeepSeek API Key", "warning");
            return;
        }

        bindButton.disabled = true;
        bindButton.textContent = "验证中...";

        try {
            const response = await fetch("/api/tokens/deepseek/bind", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ api_key: apiKey }),
            });
            const data = await response.json();

            if (data.code === 0) {
                apiKeyInput.value = "";
                setMessage(data.message || "绑定成功", true);
                renderDeepSeekAccount(data.data || {});
                window.appNotify("DeepSeek API Key 已绑定", "success");
                await loadLogs();
            } else {
                setMessage(data.message || "绑定失败", false);
                window.appNotify(data.message || "绑定失败", "error");
            }
        } catch (error) {
            setMessage("绑定失败，请检查网络或稍后重试", false);
            window.appNotify("绑定失败，请稍后重试", "error");
        } finally {
            bindButton.disabled = false;
            bindButton.textContent = "绑定并验证";
        }
    });

    refreshButton?.addEventListener("click", async () => {
        refreshButton.disabled = true;
        refreshButton.textContent = "刷新中...";
        try {
            const response = await fetch("/api/tokens/deepseek/refresh", { method: "POST" });
            const data = await response.json();
            if (data.code === 0) {
                renderDeepSeekAccount(data.data || {});
                setMessage(data.message || "余额已刷新", true);
                window.appNotify("DeepSeek 真实余额已刷新", "success");
                await loadLogs();
            } else {
                setMessage(data.message || "刷新失败", false);
                window.appNotify(data.message || "刷新失败", "error");
            }
        } catch (error) {
            setMessage("刷新失败，请稍后重试", false);
            window.appNotify("刷新失败，请稍后重试", "error");
        } finally {
            refreshButton.textContent = "刷新真实余额";
            await loadDeepSeekStatus();
        }
    });

    removeButton?.addEventListener("click", async () => {
        const confirmed = await window.appConfirm("确认移除已绑定的 DeepSeek API Key？", {
            message: "移除后本系统将无法继续显示该 Key 的真实余额，需要重新绑定。",
            confirmText: "移除",
        });
        if (!confirmed) {
            return;
        }
        try {
            const response = await fetch("/api/tokens/deepseek/key", { method: "DELETE" });
            const data = await response.json();
            if (data.code === 0) {
                renderDeepSeekAccount({ is_bound: false });
                setMessage(data.message || "已移除绑定", true);
                window.appNotify("已移除 DeepSeek API Key", "success");
                await loadLogs();
            } else {
                setMessage(data.message || "移除失败", false);
                window.appNotify(data.message || "移除失败", "error");
            }
        } catch (error) {
            setMessage("移除失败，请稍后重试", false);
            window.appNotify("移除失败，请稍后重试", "error");
        }
    });

    Promise.all([loadDeepSeekStatus(), loadStats(), loadLogs()]).catch(() => {
        window.appNotify("Token 页面部分数据加载失败", "warning");
    });
});
