document.addEventListener("DOMContentLoaded", () => {
    const appShell = document.getElementById("app-shell");
    const sidebar = document.getElementById("app-sidebar");
    const overlay = document.getElementById("app-overlay");
    const toggleButton = document.getElementById("mobile-nav-toggle");
    const sceneBackdrop = document.getElementById("scene-backdrop");
    const sceneCanvas = document.getElementById("scene-canvas");
    const isAuthPage = document.body.classList.contains("auth-page");

    initTheme();

    function closeSidebar() {
        appShell?.classList.remove("sidebar-open");
        document.body.style.overflow = "";
    }

    function openSidebar() {
        appShell?.classList.add("sidebar-open");
        document.body.style.overflow = "hidden";
    }

    toggleButton?.addEventListener("click", () => {
        if (!appShell) {
            return;
        }
        if (appShell.classList.contains("sidebar-open")) {
            closeSidebar();
        } else {
            openSidebar();
        }
    });

    overlay?.addEventListener("click", closeSidebar);

    window.addEventListener("resize", () => {
        if (window.innerWidth > 980) {
            closeSidebar();
        }
    });

    sidebar?.querySelectorAll("a").forEach((link) => {
        link.addEventListener("click", () => {
            if (window.innerWidth <= 980) {
                closeSidebar();
            }
        });
    });

    if (!isAuthPage && sceneBackdrop) {
        sceneBackdrop.setAttribute("hidden", "hidden");
    }

    if (isAuthPage && sceneBackdrop && window.matchMedia("(pointer:fine)").matches) {
        let pointerX = 0;
        let pointerY = 0;
        let currentX = 0;
        let currentY = 0;
        let ticking = false;

        function updateScene() {
            currentX += (pointerX - currentX) * 0.08;
            currentY += (pointerY - currentY) * 0.08;
            sceneBackdrop.style.setProperty("--scene-shift-x", `${currentX.toFixed(2)}px`);
            sceneBackdrop.style.setProperty("--scene-shift-y", `${currentY.toFixed(2)}px`);

            if (Math.abs(pointerX - currentX) > 0.1 || Math.abs(pointerY - currentY) > 0.1) {
                window.requestAnimationFrame(updateScene);
            } else {
                ticking = false;
            }
        }

        window.addEventListener("pointermove", (event) => {
            const normalizedX = event.clientX / window.innerWidth - 0.5;
            const normalizedY = event.clientY / window.innerHeight - 0.5;
            pointerX = normalizedX * 28;
            pointerY = normalizedY * 20;

            if (!ticking) {
                ticking = true;
                window.requestAnimationFrame(updateScene);
            }
        });
    }

    if (isAuthPage && sceneCanvas && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        setupAnimatedScene(sceneCanvas);
    }
});

function initTheme() {
    if (document.body.classList.contains("auth-page")) {
        return;
    }

    const savedTheme = window.localStorage.getItem("rs-theme");
    const preferredTheme = savedTheme === "light" ? "light" : "dark";
    applyTheme(preferredTheme);
}

function applyTheme(theme) {
    if (document.body.classList.contains("auth-page")) {
        return;
    }

    const normalizedTheme = theme === "light" ? "light" : "dark";
    document.body.dataset.theme = normalizedTheme;

    const themeIcon = document.getElementById("theme-icon");
    const themeLabel = document.getElementById("theme-label");

    if (themeIcon) {
        themeIcon.textContent = normalizedTheme === "light" ? "☀" : "🌙";
    }

    if (themeLabel) {
        themeLabel.textContent = normalizedTheme === "light" ? "浅色模式" : "深色模式";
    }

    window.localStorage.setItem("rs-theme", normalizedTheme);
}

window.toggleTheme = function toggleTheme() {
    const currentTheme = document.body.dataset.theme === "light" ? "light" : "dark";
    applyTheme(currentTheme === "light" ? "dark" : "light");
};

function setupAnimatedScene(canvas) {
    const context = canvas.getContext("2d", { alpha: true });
    if (!context) {
        return;
    }

    const particles = [];
    const dpr = Math.min(window.devicePixelRatio || 1, 1.8);
    const pointer = { x: 0, y: 0, active: false };
    let width = 0;
    let height = 0;
    let rafId = 0;
    let particleCount = 0;

    function resize() {
        width = window.innerWidth;
        height = window.innerHeight;
        canvas.width = Math.floor(width * dpr);
        canvas.height = Math.floor(height * dpr);
        canvas.style.width = `${width}px`;
        canvas.style.height = `${height}px`;
        context.setTransform(dpr, 0, 0, dpr, 0, 0);

        particleCount = Math.max(28, Math.min(52, Math.round(width / 34)));
        particles.length = 0;
        for (let index = 0; index < particleCount; index += 1) {
            particles.push(createParticle(width, height));
        }
    }

    function createParticle(viewWidth, viewHeight) {
        const depth = Math.random() * 0.9 + 0.1;
        return {
            angle: Math.random() * Math.PI * 2,
            radius: (Math.random() * 0.42 + 0.08) * Math.min(viewWidth, viewHeight),
            z: depth,
            speed: (Math.random() * 0.0025 + 0.0012) * (Math.random() > 0.5 ? 1 : -1),
            drift: Math.random() * Math.PI * 2,
            size: Math.random() * 2.4 + 1.2,
            tint: Math.random(),
        };
    }

    function drawBackground(time) {
        context.clearRect(0, 0, width, height);

        const bgGradient = context.createLinearGradient(0, 0, width, height);
        bgGradient.addColorStop(0, "rgba(24, 43, 78, 0.68)");
        bgGradient.addColorStop(0.45, "rgba(13, 29, 55, 0.26)");
        bgGradient.addColorStop(1, "rgba(8, 18, 34, 0.68)");
        context.fillStyle = bgGradient;
        context.fillRect(0, 0, width, height);

        const glowX = width * 0.72 + Math.sin(time * 0.00028) * width * 0.08;
        const glowY = height * 0.26 + Math.cos(time * 0.00021) * height * 0.06;
        const glow = context.createRadialGradient(glowX, glowY, 0, glowX, glowY, Math.max(width, height) * 0.38);
        glow.addColorStop(0, "rgba(126, 182, 255, 0.2)");
        glow.addColorStop(0.32, "rgba(126, 182, 255, 0.08)");
        glow.addColorStop(1, "rgba(126, 182, 255, 0)");
        context.fillStyle = glow;
        context.fillRect(0, 0, width, height);
    }

    function projectParticle(particle, time) {
        particle.angle += particle.speed;
        particle.drift += 0.0026;

        const depthScale = 0.58 + particle.z * 0.9;
        const pulse = Math.sin(time * 0.001 + particle.drift) * 18;
        const orbitRadius = particle.radius + pulse;
        const centerX = width * 0.54 + (pointer.active ? (pointer.x - width / 2) * 0.035 * particle.z : 0);
        const centerY = height * 0.48 + (pointer.active ? (pointer.y - height / 2) * 0.028 * particle.z : 0);
        const x = centerX + Math.cos(particle.angle) * orbitRadius;
        const y = centerY + Math.sin(particle.angle * 1.18) * orbitRadius * 0.38 - particle.z * 120;
        const scale = 0.4 + depthScale * 0.9;

        return {
            x,
            y,
            scale,
            alpha: 0.16 + particle.z * 0.42,
            size: particle.size * scale,
            tint: particle.tint,
        };
    }

    function drawScene(time) {
        drawBackground(time);

        const projected = particles.map((particle) => projectParticle(particle, time));

        for (let index = 0; index < projected.length; index += 1) {
            const pointA = projected[index];
            for (let next = index + 1; next < projected.length; next += 1) {
                const pointB = projected[next];
                const dx = pointA.x - pointB.x;
                const dy = pointA.y - pointB.y;
                const distance = Math.hypot(dx, dy);
                if (distance > 160) {
                    continue;
                }

                const alpha = (1 - distance / 160) * 0.16 * Math.min(pointA.alpha, pointB.alpha);
                context.strokeStyle = `rgba(170, 205, 255, ${alpha.toFixed(3)})`;
                context.lineWidth = 1;
                context.beginPath();
                context.moveTo(pointA.x, pointA.y);
                context.lineTo(pointB.x, pointB.y);
                context.stroke();
            }
        }

        projected.forEach((point) => {
            const fill = point.tint > 0.5
                ? `rgba(138, 189, 255, ${point.alpha.toFixed(3)})`
                : `rgba(158, 148, 255, ${point.alpha.toFixed(3)})`;
            context.fillStyle = fill;
            context.beginPath();
            context.arc(point.x, point.y, point.size, 0, Math.PI * 2);
            context.fill();
        });

        rafId = window.requestAnimationFrame(drawScene);
    }

    resize();
    rafId = window.requestAnimationFrame(drawScene);

    window.addEventListener("resize", resize);
    window.addEventListener("pointermove", (event) => {
        pointer.x = event.clientX;
        pointer.y = event.clientY;
        pointer.active = true;
    });
    window.addEventListener("pointerleave", () => {
        pointer.active = false;
    });
    window.addEventListener("beforeunload", () => {
        window.cancelAnimationFrame(rafId);
    });
}

window.appEscapeHtml = function appEscapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
};

window.appNotify = function appNotify(message, type = "info", timeout = 2400) {
    const safeMessage = String(message || "操作完成");
    let container = document.querySelector(".toast-container");

    if (!container) {
        container = document.createElement("div");
        container.className = "toast-container";
        document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = "toast";
    toast.dataset.type = type;
    toast.textContent = safeMessage;
    container.appendChild(toast);

    window.setTimeout(() => {
        toast.remove();
        if (!container.children.length) {
            container.remove();
        }
    }, timeout);
};

function openAppDialog(options) {
    const config = {
        type: "alert",
        title: "提示",
        message: "",
        defaultValue: "",
        placeholder: "",
        confirmText: "确定",
        cancelText: "取消",
        ...options,
    };

    return new Promise((resolve) => {
        const backdrop = document.createElement("div");
        backdrop.className = "app-dialog-backdrop";
        backdrop.setAttribute("role", "presentation");

        const dialog = document.createElement("section");
        dialog.className = "app-dialog";
        dialog.setAttribute("role", "dialog");
        dialog.setAttribute("aria-modal", "true");

        const title = document.createElement("h2");
        title.className = "app-dialog-title";
        title.textContent = config.title;
        dialog.appendChild(title);

        if (config.message) {
            const message = document.createElement("p");
            message.className = "app-dialog-message";
            message.textContent = config.message;
            dialog.appendChild(message);
        }

        let input = null;
        if (config.type === "prompt") {
            input = document.createElement("input");
            input.className = "app-dialog-field";
            input.type = "text";
            input.value = config.defaultValue || "";
            input.placeholder = config.placeholder || "";
            dialog.appendChild(input);
        }

        const actions = document.createElement("div");
        actions.className = "app-dialog-actions";

        const closeDialog = (value) => {
            document.removeEventListener("keydown", onKeyDown);
            backdrop.remove();
            resolve(value);
        };

        const cancelButton = document.createElement("button");
        cancelButton.type = "button";
        cancelButton.className = "btn-secondary";
        cancelButton.textContent = config.cancelText;
        cancelButton.addEventListener("click", () => closeDialog(config.type === "confirm" ? false : null));

        const confirmButton = document.createElement("button");
        confirmButton.type = "button";
        confirmButton.className = "btn-primary";
        confirmButton.textContent = config.confirmText;
        confirmButton.addEventListener("click", () => {
            if (config.type === "prompt") {
                closeDialog(input.value);
                return;
            }
            closeDialog(true);
        });

        if (config.type !== "alert") {
            actions.appendChild(cancelButton);
        }
        actions.appendChild(confirmButton);
        dialog.appendChild(actions);

        function onKeyDown(event) {
            if (event.key === "Escape") {
                closeDialog(config.type === "confirm" ? false : null);
            }
            if (event.key === "Enter" && config.type === "prompt" && document.activeElement === input) {
                closeDialog(input.value);
            }
        }

        backdrop.addEventListener("click", (event) => {
            if (event.target === backdrop) {
                closeDialog(config.type === "confirm" ? false : null);
            }
        });

        backdrop.appendChild(dialog);
        document.body.appendChild(backdrop);
        document.addEventListener("keydown", onKeyDown);

        window.setTimeout(() => {
            (input || confirmButton).focus();
            if (input) {
                input.select();
            }
        }, 0);
    });
}

window.appPrompt = function appPrompt(title, defaultValue = "", options = {}) {
    return openAppDialog({
        type: "prompt",
        title,
        defaultValue,
        message: options.message || "",
        placeholder: options.placeholder || "",
        confirmText: options.confirmText || "确定",
        cancelText: options.cancelText || "取消",
    });
};

window.appConfirm = function appConfirm(title, options = {}) {
    return openAppDialog({
        type: "confirm",
        title,
        message: options.message || "",
        confirmText: options.confirmText || "确定",
        cancelText: options.cancelText || "取消",
    });
};

window.appAlert = function appAlert(title, options = {}) {
    return openAppDialog({
        type: "alert",
        title,
        message: options.message || "",
        confirmText: options.confirmText || "确定",
    });
};

window.appCopyText = async function appCopyText(text, successMessage = "复制成功") {
    if (!text || !String(text).trim()) {
        window.appNotify("没有可复制的内容", "warning");
        return false;
    }

    try {
        await navigator.clipboard.writeText(String(text));
        window.appNotify(successMessage, "success");
        return true;
    } catch (error) {
        window.appNotify("复制失败，请重试", "error");
        return false;
    }
};

window.appFormatAuthors = function appFormatAuthors(authors) {
    if (!authors) {
        return "未知作者";
    }

    if (Array.isArray(authors)) {
        return authors.filter(Boolean).join(", ") || "未知作者";
    }

    if (typeof authors === "string") {
        try {
            const parsed = JSON.parse(authors);
            if (Array.isArray(parsed)) {
                return parsed.filter(Boolean).join(", ") || "未知作者";
            }
        } catch (error) {
            return authors || "未知作者";
        }
        return authors || "未知作者";
    }

    return "未知作者";
};
