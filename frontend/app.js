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

let activeController = null;
let toastTimer = null;

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

function appendUserMessage(text) {
    const article = document.createElement("article");
    article.className = "message user-message";

    const column = document.createElement("div");
    column.className = "message-column";

    const content = document.createElement("div");
    content.className = "message-content";
    content.textContent = text;

    column.append(content);
    article.append(column);
    messageList.append(article);
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
    sendButton.disabled = !input.value.trim() || Boolean(activeController);
}

function setStreamingState(active) {
    sendButton.hidden = active;
    stopButton.hidden = !active;
    input.disabled = active;
    conversation.setAttribute("aria-busy", String(active));
    composerStatus.textContent = active ? "正在查询制度资料" : "回答依据以现行制度原文为准";
    if (active) {
        setStatus("busy", "生成中");
    }
    resizeInput();
    refreshIcons();
}

async function askQuestion(question) {
    appendUserMessage(question);
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
            body: JSON.stringify({ question }),
            signal: activeController.signal,
        });

        if (!response.ok) {
            const detail = await response.text();
            throw new Error(detail || `请求失败（${response.status}）`);
        }

        if (!response.body) {
            throw new Error("浏览器未收到流式响应");
        }

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
    if (!question || activeController) {
        return;
    }

    input.value = "";
    resizeInput();
    askQuestion(question);
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
