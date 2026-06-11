document.addEventListener("DOMContentLoaded", () => {
    const messageBox = document.getElementById("token-msg");
    const detailBox = document.getElementById("system-account-detail");
    const discountContactButton = document.getElementById("btn-discount-contact");
    const redeemForm = document.getElementById("redeem-form");
    const redeemInput = document.getElementById("redeem-key");
    const redeemButton = document.getElementById("btn-redeem-key");
    const wechatModal = document.getElementById("wechat-contact-modal");

    function setMessage(message, ok = true) {
        if (!messageBox) {
            return;
        }
        messageBox.textContent = message || "";
        messageBox.className = ok ? "msg msg-success" : "msg msg-error";
    }

    function formatCents(value) {
        const cents = Number(value || 0);
        return `¥${(cents / 100).toLocaleString("zh-CN", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        })}`;
    }

    function formatSignedCents(value) {
        const cents = Number(value || 0);
        const sign = cents > 0 ? "+" : cents < 0 ? "-" : "";
        return `${sign}${formatCents(Math.abs(cents))}`;
    }

    function renderSystemStatus(status) {
        const balanceElement = document.getElementById("local-balance");
        const statusElement = document.getElementById("system-key-status");
        const balance = status.balance || {};
        const isConfigured = Boolean(status.is_bound);

        if (balanceElement) {
            balanceElement.textContent = balance.balance_text || formatCents(balance.balance || 0);
        }
        if (statusElement) {
            statusElement.textContent = isConfigured ? "可用" : "未配置";
        }
        if (!detailBox) {
            return;
        }

        detailBox.innerHTML = `
            <div class="deepseek-key-card">
                <div>
                    <span>系统 Key</span>
                    <strong>${window.appEscapeHtml(status.key_mask || "未配置")}</strong>
                </div>
                <div>
                    <span>扣费规则</span>
                    <strong>${window.appEscapeHtml(String(status.billing_cents_per_1000_tokens || "0"))} 分 / 1000 tokens</strong>
                </div>
            </div>
            <div class="deepseek-balance-list">
                <div class="deepseek-balance-row">
                    <span>当前额度</span>
                    <strong>${window.appEscapeHtml(balance.balance_text || formatCents(balance.balance || 0))}</strong>
                    <small>新用户注册默认赠送 5 元，AI 调用后自动扣减。</small>
                </div>
                <div class="deepseek-balance-row">
                    <span>累计充值</span>
                    <strong>${window.appEscapeHtml(balance.total_purchased_text || "¥0.00")}</strong>
                    <small>线上支付未开通，充值请联系页面下方客服微信。</small>
                </div>
            </div>
        `;
    }

    async function loadSystemStatus() {
        const response = await fetch("/api/tokens/deepseek/status");
        const data = await response.json();
        if (data.code === 0) {
            renderSystemStatus(data.data || {});
            if (data.message && data.message !== "ok") {
                setMessage(data.message, false);
            }
        } else {
            setMessage(data.message || "系统 API 状态加载失败", false);
        }
    }

    async function loadStats() {
        const response = await fetch("/api/tokens/stats");
        const data = await response.json();
        if (data.code === 0) {
            document.getElementById("today-cost").textContent = formatCents(data.data.today || 0);
            document.getElementById("week-cost").textContent = formatCents(data.data.week || 0);
        }
    }

    async function loadLogs() {
        const container = document.getElementById("token-logs");
        const response = await fetch("/api/tokens/logs");
        const data = await response.json();
        const logs = data.data || [];

        if (!container) {
            return;
        }
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
                            <th>金额</th>
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
                                    <td>${window.appEscapeHtml(log.action || "-")}</td>
                                    <td class="${amountClass}">${window.appEscapeHtml(formatSignedCents(amount))}</td>
                                    <td>${window.appEscapeHtml(log.description || "-")}</td>
                                </tr>
                            `;
                        }).join("")}
                    </tbody>
                </table>
            </div>
        `;
    }

    async function redeemKey(event) {
        event.preventDefault();
        const key = redeemInput?.value.trim() || "";

        if (!key) {
            setMessage("请输入兑换码或密钥", false);
            redeemInput?.focus();
            return;
        }

        const originalText = redeemButton?.textContent || "兑换";
        if (redeemButton) {
            redeemButton.disabled = true;
            redeemButton.textContent = "兑换中";
        }

        try {
            const response = await fetch("/api/tokens/redeem", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ key }),
            });
            const data = await response.json();
            const ok = data.code === 0;
            const message = data.message || (ok ? "兑换成功" : "兑换失败");

            setMessage(message, ok);
            window.appNotify(message, ok ? "success" : "warning");

            if (ok) {
                redeemInput.value = "";
                await Promise.all([loadSystemStatus(), loadStats(), loadLogs()]);
            }
        } catch (error) {
            setMessage("兑换请求失败，请稍后重试", false);
            window.appNotify("兑换请求失败，请稍后重试", "error");
        } finally {
            if (redeemButton) {
                redeemButton.disabled = false;
                redeemButton.textContent = originalText;
            }
        }
    }

    function openWechatModal() {
        if (!wechatModal) {
            return;
        }
        wechatModal.hidden = false;
        document.body.classList.add("modal-open");
    }

    function closeWechatModal() {
        if (!wechatModal) {
            return;
        }
        wechatModal.hidden = true;
        document.body.classList.remove("modal-open");
    }

    discountContactButton?.addEventListener("click", openWechatModal);
    redeemForm?.addEventListener("submit", redeemKey);
    wechatModal?.querySelectorAll("[data-wechat-close]").forEach((element) => {
        element.addEventListener("click", closeWechatModal);
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && wechatModal && !wechatModal.hidden) {
            closeWechatModal();
        }
    });

    Promise.all([loadSystemStatus(), loadStats(), loadLogs()]).catch(() => {
        window.appNotify("Token 页面部分数据加载失败", "warning");
    });
});
