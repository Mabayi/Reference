document.addEventListener("DOMContentLoaded", () => {
    const faqContainer = document.getElementById("support-faqs");
    const faqAnswerPanel = document.getElementById("support-faq-answer");
    const faqAnswerText = document.getElementById("support-faq-answer-text");
    const subjectInput = document.getElementById("support-subject");
    const messageInput = document.getElementById("support-message");
    const submitButton = document.getElementById("btn-submit-ticket");
    const askAiButton = document.getElementById("btn-ask-ai");
    const aiResult = document.getElementById("support-ai-result");
    const ticketList = document.getElementById("support-ticket-list");

    let selectedFaq = "";
    let faqItems = [];

    function statusText(status) {
        const map = {
            open: "待处理",
            in_progress: "处理中",
            resolved: "已解决",
            closed: "已关闭",
        };
        return map[status] || status || "-";
    }

    function feedbackText(feedback) {
        const map = {
            helpful: "有效",
            not_helpful: "无效",
        };
        return map[feedback] || "";
    }

    function selectedFaqItem() {
        return faqItems.find((item) => item.key === selectedFaq) || {};
    }

    function validateInput() {
        const subject = subjectInput.value.trim();
        const message = messageInput.value.trim();
        if (!subject) {
            window.appNotify("请填写问题标题", "warning");
            return null;
        }
        if (message.length < 8) {
            window.appNotify("请补充更具体的问题描述", "warning");
            return null;
        }
        return { subject, message, faq_key: selectedFaq };
    }

    function renderFeedbackActions(ticket) {
        if (!ticket.ai_reply) {
            return "";
        }
        if (ticket.feedback) {
            return `<div class="ticket-feedback-result">用户反馈：${window.appEscapeHtml(feedbackText(ticket.feedback))}</div>`;
        }
        return `
            <div class="ticket-feedback-actions" data-ticket-id="${window.appEscapeHtml(ticket.id)}">
                <span>这条 AI 回复是否有效？</span>
                <button class="btn-secondary btn-ticket-feedback" type="button" data-helpful="1">有效</button>
                <button class="btn-secondary btn-ticket-feedback" type="button" data-helpful="0">无效</button>
            </div>
        `;
    }

    function renderTickets(tickets) {
        if (!tickets.length) {
            ticketList.innerHTML = '<p class="empty-hint">暂无工单记录。</p>';
            return;
        }

        ticketList.innerHTML = tickets.map((ticket) => `
            <article class="support-ticket-card">
                <div class="support-ticket-head">
                    <div>
                        <strong>${window.appEscapeHtml(ticket.subject || "未命名问题")}</strong>
                        <p>${window.appEscapeHtml(ticket.created_at || "-")}</p>
                    </div>
                    <span class="status-pill" data-status="${window.appEscapeHtml(ticket.status || "open")}">${statusText(ticket.status)}</span>
                </div>
                <div class="ticket-meta-row">
                    <span>来源：${ticket.source === "ai" ? "AI 咨询" : "人工工单"}</span>
                    <span>分类：${window.appEscapeHtml(ticket.category || "其他")}</span>
                    <span>情绪：${window.appEscapeHtml(ticket.sentiment || "中性")} ${window.appEscapeHtml(ticket.sentiment_score || 2)}/5</span>
                    <span>优先级：${window.appEscapeHtml(ticket.priority || "普通")}</span>
                </div>
                <p class="ticket-message">${window.appEscapeHtml(ticket.message || "")}</p>
                ${ticket.faq_answer ? `<p class="ticket-faq-answer">固定解答：${window.appEscapeHtml(ticket.faq_answer)}</p>` : ""}
                ${ticket.ai_reply ? `<p class="ticket-ai-reply">AI 回复：${window.appEscapeHtml(ticket.ai_reply)}</p>` : ""}
                ${ticket.ai_summary ? `<p class="ticket-ai-summary">AI 摘要：${window.appEscapeHtml(ticket.ai_summary)}</p>` : ""}
                ${renderFeedbackActions(ticket)}
                ${ticket.admin_reply ? `
                    <div class="ticket-reply">
                        <strong>客服回复</strong>
                        <p>${window.appEscapeHtml(ticket.admin_reply)}</p>
                    </div>
                ` : ""}
            </article>
        `).join("");
    }

    function renderAiResult(ticket, aiReply) {
        aiResult.hidden = false;
        aiResult.innerHTML = `
            <strong>AI 回复</strong>
            <p>${window.appEscapeHtml(aiReply || "AI 已处理你的问题。")}</p>
            <div class="ticket-feedback-actions" data-ticket-id="${window.appEscapeHtml(ticket.id)}">
                <span>这条回复是否有效？</span>
                <button class="btn-secondary btn-ticket-feedback" type="button" data-helpful="1">有效</button>
                <button class="btn-secondary btn-ticket-feedback" type="button" data-helpful="0">无效</button>
            </div>
        `;
    }

    async function loadFaqs() {
        const response = await fetch("/api/support/faqs");
        const data = await response.json();
        faqItems = data.data || [];
        faqContainer.innerHTML = faqItems.map((item) => `
            <button class="support-faq-chip" type="button" data-key="${window.appEscapeHtml(item.key)}">
                <strong>${window.appEscapeHtml(item.title)}</strong>
                <span>${window.appEscapeHtml(item.answer || "")}</span>
            </button>
        `).join("");
    }

    async function loadTickets() {
        const response = await fetch("/api/support/tickets");
        const data = await response.json();
        renderTickets(data.data || []);
    }

    faqContainer?.addEventListener("click", (event) => {
        const button = event.target.closest(".support-faq-chip");
        if (!button) {
            return;
        }
        selectedFaq = button.dataset.key || "";
        faqContainer.querySelectorAll(".support-faq-chip").forEach((item) => {
            item.classList.toggle("active", item === button);
        });
        const faq = selectedFaqItem();
        if (!subjectInput.value.trim()) {
            subjectInput.value = faq.title || button.textContent.trim();
        }
        faqAnswerText.textContent = faq.answer || "暂无固定答案。";
        faqAnswerPanel.hidden = false;
    });

    async function createManualTicket() {
        const payload = validateInput();
        if (!payload) {
            return;
        }

        submitButton.disabled = true;
        submitButton.textContent = "提交中...";
        try {
            const response = await fetch("/api/support/tickets", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            const data = await response.json();
            if (data.code !== 0) {
                window.appNotify(data.message || "提交失败", "error");
                return;
            }
            window.appNotify("人工工单已提交", "success");
            await loadTickets();
        } catch (error) {
            window.appNotify("提交失败，请稍后重试", "error");
        } finally {
            submitButton.disabled = false;
            submitButton.textContent = "提交人工工单";
        }
    }

    async function askSupportAi() {
        const payload = validateInput();
        if (!payload) {
            return;
        }

        askAiButton.disabled = true;
        askAiButton.textContent = "AI 回复中...";
        try {
            const response = await fetch("/api/support/ai", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            const data = await response.json();
            if (data.code !== 0) {
                window.appNotify(data.message || "AI 回复失败", "error");
                return;
            }
            const ticket = data.data?.ticket || {};
            renderAiResult(ticket, data.data?.ai_reply || ticket.ai_reply);
            window.appNotify("AI 已回复，并已创建工单", "success");
            await loadTickets();
        } catch (error) {
            window.appNotify("AI 回复失败，请稍后重试", "error");
        } finally {
            askAiButton.disabled = false;
            askAiButton.textContent = "询问 AI 并创建工单";
        }
    }

    async function submitFeedback(button) {
        const wrapper = button.closest(".ticket-feedback-actions");
        const ticketId = wrapper?.dataset.ticketId;
        if (!ticketId) {
            return;
        }
        const helpful = button.dataset.helpful === "1";
        wrapper.querySelectorAll("button").forEach((item) => {
            item.disabled = true;
        });
        try {
            const response = await fetch(`/api/support/tickets/${ticketId}/feedback`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ helpful }),
            });
            const data = await response.json();
            if (data.code !== 0) {
                window.appNotify(data.message || "反馈失败", "error");
                return;
            }
            window.appNotify("反馈已记录", "success");
            await loadTickets();
        } catch (error) {
            window.appNotify("反馈失败，请稍后重试", "error");
        } finally {
            wrapper.querySelectorAll("button").forEach((item) => {
                item.disabled = false;
            });
        }
    }

    submitButton?.addEventListener("click", createManualTicket);
    askAiButton?.addEventListener("click", askSupportAi);

    document.addEventListener("click", (event) => {
        const button = event.target.closest(".btn-ticket-feedback");
        if (button) {
            submitFeedback(button);
        }
    });

    Promise.all([loadFaqs(), loadTickets()]).catch(() => {
        window.appNotify("客服中心部分数据加载失败", "warning");
    });
});
