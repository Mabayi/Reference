document.addEventListener("DOMContentLoaded", () => {
    const uploadArea = document.getElementById("upload-area");
    const fileInput = document.getElementById("file-input");
    const folderInput = document.getElementById("folder-input");
    const paperList = document.getElementById("paper-list");
    const folderTree = document.getElementById("folder-tree");
    const searchInput = document.getElementById("paper-search");
    const libraryTitle = document.getElementById("library-title");
    const librarySubtitle = document.getElementById("library-subtitle");
    const uploadMessage = document.getElementById("upload-message");
    const currentFolderLabel = document.getElementById("current-folder-label");
    const defaultUploadText = "拖拽 PDF 到这里上传到";

    let folders = [];
    let selectedFolderId = null;
    let selectedScope = "all";
    let searchQuery = "";

    function folderNameById(id) {
        const folder = folders.find((item) => Number(item.id) === Number(id));
        return folder?.name || "未命名文件夹";
    }

    function setUploadState(message, uploading = false) {
        if (uploadMessage) {
            uploadMessage.textContent = message;
        }
        uploadArea?.classList.toggle("uploading", uploading);
    }

    async function readApiResponse(response) {
        let data = null;
        try {
            data = await response.json();
        } catch (error) {
            data = null;
        }

        if (response.status === 422) {
            return {
                code: 1,
                data: null,
                message: "文件夹接口未生效，请重启后端服务后再试。",
            };
        }

        if (!response.ok) {
            return {
                code: 1,
                data: null,
                message: data?.message || `请求失败（${response.status}）`,
            };
        }

        return data || { code: 1, data: null, message: "接口返回异常" };
    }

    function renderEmptyState() {
        paperList.innerHTML = `
            <div class="empty-state">
                <h4>没有找到文献</h4>
                <p>可以上传 PDF，或切换文件夹和搜索条件后再查看。</p>
            </div>
        `;
    }

    function getFolderDepth(folder) {
        let depth = 0;
        let parentId = folder.parent_id;
        while (parentId) {
            const parent = folders.find((item) => Number(item.id) === Number(parentId));
            if (!parent) {
                break;
            }
            depth += 1;
            parentId = parent.parent_id;
        }
        return depth;
    }

    function getOrderedFolders(parentId = null) {
        const children = folders
            .filter((folder) => {
                if (parentId === null) {
                    return !folder.parent_id;
                }
                return Number(folder.parent_id) === Number(parentId);
            })
            .sort((left, right) => String(left.name || "").localeCompare(String(right.name || ""), "zh-CN"));

        return children.flatMap((folder) => [folder, ...getOrderedFolders(folder.id)]);
    }

    function renderFolders() {
        const allActive = selectedScope === "all";
        const rootActive = selectedScope === "root";
        const rows = [
            `<button class="folder-item ${allActive ? "active" : ""}" data-scope="all" type="button">
                <span>全部文献</span>
                <strong>ALL</strong>
            </button>`,
            `<button class="folder-item ${rootActive ? "active" : ""}" data-scope="root" type="button">
                <span>未归档</span>
                <strong>-</strong>
            </button>`,
        ];

        getOrderedFolders().forEach((folder) => {
            const active = selectedScope === "folder" && Number(selectedFolderId) === Number(folder.id);
            const depth = getFolderDepth(folder);
            rows.push(`
                <button class="folder-item ${active ? "active" : ""}" data-scope="folder" data-id="${folder.id}" type="button" style="--folder-depth:${depth};">
                    <span>${window.appEscapeHtml(folder.name)}</span>
                    <strong>${Number(folder.paper_count || 0)}</strong>
                </button>
            `);
        });

        folderTree.innerHTML = rows.join("");
        folderTree.querySelectorAll(".folder-item").forEach((button) => {
            button.addEventListener("click", () => {
                selectedScope = button.dataset.scope || "all";
                selectedFolderId = button.dataset.id ? Number(button.dataset.id) : null;
                updateContextLabels();
                renderFolders();
                loadPapers();
            });
        });
    }

    function updateContextLabels() {
        let title = "全部文献";
        if (selectedScope === "root") {
            title = "未归档文献";
        } else if (selectedScope === "folder") {
            title = folderNameById(selectedFolderId);
        }

        libraryTitle.textContent = title;
        currentFolderLabel.textContent = selectedScope === "folder" ? title : "未归档";
        librarySubtitle.textContent = searchQuery ? `搜索：${searchQuery}` : "支持搜索、阅读、重命名和删除";
    }

    function renderFolderSelect(paper) {
        const currentFolderId = paper.folder_id == null ? "" : String(paper.folder_id);
        const options = [
            `<option value="" ${currentFolderId === "" ? "selected" : ""}>未归档</option>`,
            ...getOrderedFolders().map((folder) => {
                const value = String(folder.id);
                const prefix = "　".repeat(getFolderDepth(folder));
                return `<option value="${value}" ${currentFolderId === value ? "selected" : ""}>${prefix}${window.appEscapeHtml(folder.name)}</option>`;
            }),
        ];

        return `
            <select class="paper-folder-select" data-id="${paper.id}" data-previous-folder="${currentFolderId}" aria-label="移动到文件夹">
                ${options.join("")}
            </select>
        `;
    }

    function renderPapers(papers) {
        if (!papers || !papers.length) {
            renderEmptyState();
            return;
        }

        const rows = papers.map((paper) => {
            const title = paper.title || paper.filename || "未命名文献";
            const authors = window.appFormatAuthors(paper.authors);
            const year = paper.year || "-";
            const folderName = paper.folder_name || "未归档";

            let statusClass = "badge badge-pending";
            let statusText = "等待解析";

            if (paper.parse_status === "done") {
                statusClass = "badge badge-done";
                statusText = "解析完成";
            } else if (paper.parse_status === "failed") {
                statusClass = "badge badge-failed";
                statusText = "解析失败";
            } else if (paper.parse_status === "processing") {
                statusClass = "badge badge-pending";
                statusText = "解析中";
            }

            const readButton = paper.parse_status === "done"
                ? `<a href="/reader/${paper.id}" class="btn-secondary">阅读</a>`
                : "";

            return `
                <article class="paper-row-card">
                    <div class="paper-row-main">
                        <div class="paper-title-cell">
                            <strong>${window.appEscapeHtml(title)}</strong>
                            <span class="table-muted">${window.appEscapeHtml(paper.filename || "")}</span>
                        </div>
                        <div class="paper-row-meta">
                            <span>文件夹：${window.appEscapeHtml(folderName)}</span>
                            <span>作者：${window.appEscapeHtml(authors)}</span>
                            <span>年份：${window.appEscapeHtml(String(year))}</span>
                        </div>
                    </div>
                    <div class="paper-row-folder">
                        ${renderFolderSelect(paper)}
                    </div>
                    <div class="paper-row-status">
                        <span class="${statusClass}">${statusText}</span>
                    </div>
                    <div class="paper-row-actions">
                        ${readButton}
                        <button class="btn-secondary paper-rename" data-id="${paper.id}" data-name="${window.appEscapeHtml(paper.filename || "")}" type="button">重命名</button>
                        <button class="btn-danger paper-delete" data-id="${paper.id}" type="button">删除</button>
                    </div>
                </article>
            `;
        }).join("");

        paperList.innerHTML = `
            <div class="paper-row-list">
                ${rows}
            </div>
        `;

        paperList.querySelectorAll(".paper-rename").forEach((button) => {
            button.addEventListener("click", () => {
                window.renamePaper(Number(button.dataset.id), button.dataset.name || "");
            });
        });
        paperList.querySelectorAll(".paper-delete").forEach((button) => {
            button.addEventListener("click", () => {
                window.deletePaper(Number(button.dataset.id));
            });
        });
        paperList.querySelectorAll(".paper-folder-select").forEach((select) => {
            select.addEventListener("change", () => {
                window.movePaperToFolder(Number(select.dataset.id), select.value, select);
            });
        });

        if (papers.some((paper) => paper.parse_status === "pending" || paper.parse_status === "processing")) {
            window.setTimeout(loadPapers, 2500);
        }
    }

    async function loadFolders() {
        try {
            const response = await fetch("/api/papers/folders");
            const data = await response.json();
            folders = data.code === 0 ? (data.data || []) : [];
            renderFolders();
        } catch (error) {
            folders = [];
            renderFolders();
        }
    }

    async function loadPapers() {
        try {
            const params = new URLSearchParams();
            params.set("scope", selectedScope);
            if (selectedScope === "folder" && selectedFolderId) {
                params.set("folder_id", String(selectedFolderId));
            }
            if (searchQuery) {
                params.set("q", searchQuery);
            }

            const response = await fetch(`/api/papers?${params.toString()}`);
            const data = await response.json();
            if (data.code !== 0) {
                renderEmptyState();
                return;
            }
            renderPapers(data.data || []);
        } catch (error) {
            paperList.innerHTML = `
                <div class="empty-state">
                    <h4>文献列表加载失败</h4>
                    <p>请刷新页面后重试。</p>
                </div>
            `;
        }
    }

    async function uploadFile(file) {
        if (!file || !file.name.toLowerCase().endsWith(".pdf")) {
            window.appNotify("当前只支持上传 PDF 文件", "warning");
            return;
        }

        const formData = new FormData();
        formData.append("file", file);
        if (selectedScope === "folder" && selectedFolderId) {
            formData.append("folder_id", String(selectedFolderId));
        }

        try {
            setUploadState("上传中，请稍候...", true);
            const response = await fetch("/api/papers/upload", {
                method: "POST",
                body: formData,
            });
            const data = await response.json();

            if (data.code !== 0) {
                window.appNotify(data.message || "上传失败", "error");
                return;
            }

            window.appNotify("上传成功，后台正在解析", "success");
            await loadFolders();
            loadPapers();
        } catch (error) {
            window.appNotify("上传失败，请稍后重试", "error");
        } finally {
            setUploadState(defaultUploadText, false);
            if (fileInput) {
                fileInput.value = "";
            }
        }
    }

    async function uploadFolderFiles(fileList) {
        const files = Array.from(fileList || []).filter((file) => file.name.toLowerCase().endsWith(".pdf"));
        if (!files.length) {
            window.appNotify("该文件夹内没有 PDF 文件", "warning");
            return;
        }

        const formData = new FormData();
        files.forEach((file) => {
            formData.append("files", file);
            formData.append("paths", file.webkitRelativePath || file.name);
        });

        try {
            setUploadState(`正在上传文件夹：${files.length} 个 PDF...`, true);
            const response = await fetch("/api/papers/upload-folder", {
                method: "POST",
                body: formData,
            });
            const data = await response.json();
            if (data.code !== 0) {
                window.appNotify(data.message || "文件夹上传失败", "error");
                return;
            }
            window.appNotify(data.message || "文件夹上传完成", "success", 3600);
            await loadFolders();
            loadPapers();
        } catch (error) {
            window.appNotify("文件夹上传失败，请稍后重试", "error");
        } finally {
            setUploadState(defaultUploadText, false);
            if (folderInput) {
                folderInput.value = "";
            }
        }
    }

    document.getElementById("btn-upload-file")?.addEventListener("click", () => fileInput?.click());
    document.getElementById("btn-upload-folder")?.addEventListener("click", () => folderInput?.click());
    document.getElementById("btn-search")?.addEventListener("click", () => {
        searchQuery = searchInput.value.trim();
        updateContextLabels();
        loadPapers();
    });
    document.getElementById("btn-new-folder")?.addEventListener("click", async () => {
        const name = (await window.appPrompt("新建文件夹", "", {
            placeholder: "请输入文件夹名称",
        }))?.trim();
        if (!name) {
            return;
        }
        const parent_id = selectedScope === "folder" ? selectedFolderId : null;
        try {
            const response = await fetch("/api/papers/folders", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name, parent_id }),
            });
            const data = await readApiResponse(response);
            if (data.code !== 0) {
                window.appNotify(data.message || "创建失败", "error");
                return;
            }
            window.appNotify("文件夹已创建", "success");
            await loadFolders();
        } catch (error) {
            window.appNotify("创建失败，请确认后端服务已重启。", "error");
        }
    });

    searchInput?.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            searchQuery = searchInput.value.trim();
            updateContextLabels();
            loadPapers();
        }
    });

    uploadArea?.addEventListener("dragover", (event) => {
        event.preventDefault();
        uploadArea.classList.add("dragover");
    });

    uploadArea?.addEventListener("dragleave", () => {
        uploadArea.classList.remove("dragover");
    });

    uploadArea?.addEventListener("drop", (event) => {
        event.preventDefault();
        uploadArea.classList.remove("dragover");
        const files = Array.from(event.dataTransfer?.files || []);
        if (files.length > 1) {
            files.forEach(uploadFile);
        } else if (files[0]) {
            uploadFile(files[0]);
        }
    });

    uploadArea?.addEventListener("click", () => {
        fileInput?.click();
    });

    fileInput?.addEventListener("change", () => {
        const file = fileInput.files?.[0];
        if (file) {
            uploadFile(file);
        }
    });

    folderInput?.addEventListener("change", () => {
        uploadFolderFiles(folderInput.files);
    });

    window.renamePaper = async function renamePaper(id, currentName) {
        const nextName = (await window.appPrompt("重命名文献", currentName || "", {
            placeholder: "请输入新的文件名",
        }))?.trim();
        if (!nextName) {
            return;
        }

        try {
            const response = await fetch(`/api/papers/${id}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ filename: nextName }),
            });
            const data = await response.json();
            if (data.code !== 0) {
                window.appNotify(data.message || "重命名失败", "error");
                return;
            }
            window.appNotify("文件名已更新", "success");
            loadPapers();
        } catch (error) {
            window.appNotify("重命名失败，请稍后再试", "error");
        }
    };

    window.movePaperToFolder = async function movePaperToFolder(id, folderValue, select) {
        const previousFolder = select?.dataset.previousFolder || "";
        const folderId = folderValue ? Number(folderValue) : null;
        try {
            if (select) {
                select.disabled = true;
            }
            const response = await fetch(`/api/papers/${id}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ folder_id: folderId }),
            });
            const data = await response.json();
            if (data.code !== 0) {
                if (select) {
                    select.value = previousFolder;
                }
                window.appNotify(data.message || "归类更新失败", "error");
                return;
            }
            if (select) {
                select.dataset.previousFolder = folderValue;
            }
            await loadFolders();
            if (selectedScope === "folder" || selectedScope === "root") {
                loadPapers();
            }
            window.appNotify("文献归类已更新", "success");
        } catch (error) {
            if (select) {
                select.value = previousFolder;
            }
            window.appNotify("归类更新失败，请稍后再试", "error");
        } finally {
            if (select) {
                select.disabled = false;
            }
        }
    };

    window.deletePaper = async function deletePaper(id) {
        const confirmed = await window.appConfirm("确认删除这篇文献吗？", {
            message: "该操作会同时移除已上传文件，无法从文献库中恢复。",
            confirmText: "删除",
        });
        if (!confirmed) {
            return;
        }

        try {
            const response = await fetch(`/api/papers/${id}`, { method: "DELETE" });
            const data = await response.json();
            if (data.code !== 0) {
                window.appNotify(data.message || "删除失败", "error");
                return;
            }

            window.appNotify("文献已删除", "success");
            await loadFolders();
            loadPapers();
        } catch (error) {
            window.appNotify("删除失败，请稍后再试", "error");
        }
    };

    updateContextLabels();
    Promise.all([loadFolders(), loadPapers()]);
});
