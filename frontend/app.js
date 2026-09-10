const form = document.querySelector("#chat-form");
const input = document.querySelector("#question-input");
const sendButton = document.querySelector("#send-button");
const stopButton = document.querySelector("#stop-button");
const messageList = document.querySelector("#message-list");
const conversation = document.querySelector("#conversation");
const characterCount = document.querySelector("#character-count");
const composerStatus = document.querySelector("#composer-status");
const topbarStatus = document.querySelector("#topbar-status");
const toast = document.querySelector("#toast");
const newChatButton = document.querySelector("#new-chat-button");
const sidebar = document.querySelector("#sidebar");
const sidebarOverlay = document.querySelector("#sidebar-overlay");
const mobileMenu = document.querySelector("#mobile-menu");
const composer = document.querySelector(".composer");
const attachButton = document.querySelector("#attach-button");
const attachmentInput = document.querySelector("#attachment-input");
const attachmentList = document.querySelector("#attachment-list");

let activeController = null;
let toastTimer = null;
let uploadInProgress = false;
let selectedAttachments = [];

const MAX_ATTACHMENTS = 5;
const MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024;

function refreshIcons() {
    if (window.lucide) {
        window.lucide.createIcons({ attrs: { "aria-hidden": "true" } });
    }
}

function setStatus(state, text) {
    topbarStatus.classList.toggle("busy", state === "busy");
    topbarStatus.classList.toggle("error", state === "error");
    topbarStatus.querySelector("span:last-child").textContent = text;
}

function showToast(message) {
    window.clearTimeout(toastTimer);
    toast.textContent = message;
    toast.hidden = false;
    toastTimer = window.setTimeout(() => {
        toast.hidden = true;
    }, 3200);
}

function scrollToLatest(behavior = "smooth") {
    conversation.scrollTo({
        top: conversation.scrollHeight,
        behavior,
    });
}

function createAssistantMessage() {
    const article = document.createElement("article");
    article.className = "message assistant-message";
    article.innerHTML = `
        <div class="assistant-avatar" aria-hidden="true">
            <i data-lucide="landmark"></i>
        </div>
        <div class="message-column">
            <div class="message-sender">制度助手</div>
            <div class="message-content streaming-cursor"></div>
            <div class="message-actions" hidden>
                <button class="message-action copy-action" type="button" title="复制回答" aria-label="复制回答">
                    <i data-lucide="copy"></i>
                </button>
            </div>
        </div>
    `;
    messageList.append(article);
    refreshIcons();
    return article;
}

function formatFileSize(size) {
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function attachmentIcon(contentType) {
    return contentType?.startsWith("image/") ? "image" : "file-text";
}

function setIdleComposerStatus() {
    composerStatus.textContent = selectedAttachments.length
        ? "附件已就绪，发送后将读取内容"
        : "回答依据以现行制度原文为准";
}

function renderAttachments() {
    attachmentList.replaceChildren();
    attachmentList.hidden = selectedAttachments.length === 0;

    for (const attachment of selectedAttachments) {
        const item = document.createElement("div");
        item.className = "attachment-item";

        const icon = document.createElement("i");
        icon.dataset.lucide = attachmentIcon(attachment.content_type);

        const copy = document.createElement("span");
        copy.className = "attachment-copy";
        const name = document.createElement("strong");
        name.textContent = attachment.name;
        const size = document.createElement("small");
        size.textContent = formatFileSize(attachment.size);

        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "attachment-remove";
        remove.title = "移除附件";
        remove.setAttribute("aria-label", `移除 ${attachment.name}`);
        remove.innerHTML = '<i data-lucide="x" aria-hidden="true"></i>';
        remove.addEventListener("click", () => removeAttachment(attachment));

        copy.append(name, size);
        item.append(icon, copy, remove);
        attachmentList.append(item);
    }
    refreshIcons();
}

async function parseError(response) {
    try {
        const payload = await response.json();
        return payload.detail || `请求失败（${response.status}）`;
    } catch {
        return `请求失败（${response.status}）`;
    }
}

async function uploadAttachments(fileList) {
    const files = Array.from(fileList);
    if (!files.length || uploadInProgress) return;

    if (selectedAttachments.length + files.length > MAX_ATTACHMENTS) {
        showToast(`每条消息最多添加 ${MAX_ATTACHMENTS} 个附件`);
        return;
    }
    const oversized = files.find((file) => file.size > MAX_ATTACHMENT_SIZE);
    if (oversized) {
        showToast(`${oversized.name} 超过 10 MB`);
        return;
    }

    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));
    uploadInProgress = true;
    attachButton.disabled = true;
    composer.classList.add("uploading");
    composerStatus.textContent = `正在上传 ${files.length} 个附件`;
    resizeInput();

    try {
        const response = await fetch("/attachments", {
            method: "POST",
            credentials: "include",
            body: formData,
        });
        if (!response.ok) throw new Error(await parseError(response));

        const payload = await response.json();
        selectedAttachments.push(...payload.attachments);
        renderAttachments();
        showToast(`已添加 ${payload.attachments.length} 个附件`);
    } catch (error) {
        showToast(error.message || "附件上传失败");
    } finally {
        uploadInProgress = false;
        attachButton.disabled = Boolean(activeController);
        composer.classList.remove("uploading");
        setIdleComposerStatus();
        attachmentInput.value = "";
        resizeInput();
    }
}

async function removeAttachment(attachment) {
    try {
        const response = await fetch(`/attachments/${attachment.id}`, {
            method: "DELETE",
            credentials: "include",
        });
        if (!response.ok && response.status !== 404) {
            throw new Error(await parseError(response));
        }
        selectedAttachments = selectedAttachments.filter((item) => item.id !== attachment.id);
        renderAttachments();
        setIdleComposerStatus();
    } catch (error) {
        showToast(error.message || "附件移除失败");
    }
}

function appendUserMessage(text, attachments = []) {
    const article = document.createElement("article");
    article.className = "message user-message";

    const column = document.createElement("div");
    column.className = "message-column";

    const content = document.createElement("div");
    content.className = "message-content";
    content.textContent = text;

    column.append(content);
    if (attachments.length) {
        const files = document.createElement("div");
        files.className = "message-attachments";
        for (const attachment of attachments) {
            const file = document.createElement("span");
            file.innerHTML = `<i data-lucide="${attachmentIcon(attachment.content_type)}" aria-hidden="true"></i>`;
            const label = document.createElement("span");
            label.textContent = attachment.name;
            file.append(label);
            files.append(file);
        }
        column.append(files);
    }
    article.append(column);
    messageList.append(article);
    refreshIcons();
}

function finishAssistantMessage(article, text) {
    const content = article.querySelector(".message-content");
    const actions = article.querySelector(".message-actions");
    const copyButton = article.querySelector(".copy-action");

    content.classList.remove("streaming-cursor");
    actions.hidden = !text;
    copyButton?.addEventListener("click", async () => {
        try {
            await navigator.clipboard.writeText(text);
            showToast("回答已复制");
        } catch {
            showToast("复制失败，请手动选择文本");
        }
    });
}

function resizeInput() {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 150)}px`;
    characterCount.textContent = `${input.value.length} / 2000`;
    sendButton.disabled = !input.value.trim() || Boolean(activeController) || uploadInProgress;
}

function setStreamingState(active) {
    sendButton.hidden = active;
    stopButton.hidden = !active;
    input.disabled = active;
    attachButton.disabled = active || uploadInProgress;
    conversation.setAttribute("aria-busy", String(active));
    if (active) {
        composerStatus.textContent = "正在查询制度资料";
    } else {
        setIdleComposerStatus();
    }
    if (active) {
        setStatus("busy", "生成中");
    }
    resizeInput();
    refreshIcons();
}

async function askQuestion(question, attachments) {
    appendUserMessage(question, attachments);
    const assistantMessage = createAssistantMessage();
    const assistantContent = assistantMessage.querySelector(".message-content");
    scrollToLatest();

    activeController = new AbortController();
    setStreamingState(true);

    let answer = "";

    try {
        const response = await fetch("/get_question", {
            method: "POST",
            credentials: "include",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                question,
                attachment_ids: attachments.map((attachment) => attachment.id),
            }),
            signal: activeController.signal,
        });

        if (!response.ok) {
            const detail = await response.text();
            throw new Error(detail || `请求失败（${response.status}）`);
        }

        if (!response.body) {
            throw new Error("浏览器未收到流式响应");
        }

        selectedAttachments = [];
        renderAttachments();

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");

        while (true) {
            const { value, done } = await reader.read();
            if (done) {
                answer += decoder.decode();
                break;
            }

            answer += decoder.decode(value, { stream: true });
            assistantContent.textContent = answer;
            scrollToLatest("auto");
        }

        if (!answer.trim()) {
            throw new Error("未收到有效回答");
        }

        setStatus("ready", "就绪");
    } catch (error) {
        if (error.name === "AbortError") {
            if (!answer) {
                assistantContent.textContent = "回答已停止。";
            }
            showToast("已停止生成");
            setStatus("ready", "已停止");
        } else {
            assistantContent.textContent = answer || "暂时无法连接制度服务，请稍后重试。";
            showToast(error.message || "请求失败");
            setStatus("error", "连接异常");
        }
    } finally {
        finishAssistantMessage(assistantMessage, answer);
        activeController = null;
        setStreamingState(false);
        input.focus();
        scrollToLatest();
    }
}

form.addEventListener("submit", (event) => {
    event.preventDefault();
    const question = input.value.trim();
    if (!question || activeController || uploadInProgress) {
        return;
    }

    const attachments = [...selectedAttachments];
    input.value = "";
    resizeInput();
    askQuestion(question, attachments);
});

input.addEventListener("input", resizeInput);
input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
        event.preventDefault();
        form.requestSubmit();
    }
});

stopButton.addEventListener("click", () => {
    activeController?.abort();
});

attachButton.addEventListener("click", () => attachmentInput.click());
attachmentInput.addEventListener("change", () => uploadAttachments(attachmentInput.files));

for (const eventName of ["dragenter", "dragover"]) {
    composer.addEventListener(eventName, (event) => {
        event.preventDefault();
        if (!activeController) composer.classList.add("drag-active");
    });
}

for (const eventName of ["dragleave", "drop"]) {
    composer.addEventListener(eventName, (event) => {
        event.preventDefault();
        composer.classList.remove("drag-active");
    });
}

composer.addEventListener("drop", (event) => {
    if (!activeController) uploadAttachments(event.dataTransfer.files);
});

document.querySelectorAll("[data-prompt]").forEach((button) => {
    button.addEventListener("click", () => {
        if (activeController) {
            return;
        }
        input.value = button.dataset.prompt;
        resizeInput();
        form.requestSubmit();
    });
});

newChatButton.addEventListener("click", async () => {
    if (activeController) {
        activeController.abort();
    }

    try {
        await fetch("/new_chat", {
            method: "POST",
            credentials: "include",
        });
    } catch {
        showToast("会话重置请求失败");
    }

    messageList.querySelectorAll(".message:not(.welcome-message)").forEach((message) => message.remove());
    closeSidebar();
    input.value = "";
    selectedAttachments = [];
    renderAttachments();
    setIdleComposerStatus();
    resizeInput();
    input.focus();
    showToast("已开始新对话");
});

function openSidebar() {
    sidebar.classList.add("open");
    sidebarOverlay.hidden = false;
}

function closeSidebar() {
    sidebar.classList.remove("open");
    sidebarOverlay.hidden = true;
}

mobileMenu.addEventListener("click", openSidebar);
sidebarOverlay.addEventListener("click", closeSidebar);
window.addEventListener("resize", () => {
    if (window.innerWidth > 780) {
        closeSidebar();
    }
});

window.addEventListener("DOMContentLoaded", () => {
    refreshIcons();
    resizeInput();
    input.focus();
});
