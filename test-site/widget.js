/**
 * AI Support Widget
 * Embeddable chat widget for customer support
 */

(function () {
  if (window.AISupportWidget) {
    console.warn("AI Support Widget already initialized");
    return;
  }

  const DEFAULT_CONFIG = {
    apiKey: "",
    baseUrl: "http://localhost:8000",
    primaryColor: "#0ea5e9",
    title: "AI Support",
    subtitle: "We're here to help",
    position: "bottom-right",
    showBranding: true,
  };

  class AISupportWidget {
    constructor(config) {
      this.config = { ...DEFAULT_CONFIG, ...config };
      this.isOpen = false;
      this.conversationId = this.generateConversationId();
      this.messages = [];

      this.injectStyles();
      this.createWidget();
      this.setupEventListeners();

      console.log("AI Support Widget initialized");
    }

    generateConversationId() {
      return "widget-" + Date.now() + "-" + Math.random().toString(36).substr(2, 9);
    }

    injectStyles() {
      const style = document.createElement("style");
      style.textContent = `
        #ai-widget-container {
          position: fixed;
          ${this.config.position === "bottom-left" ? "left" : "right"}: 20px;
          bottom: 20px;
          z-index: 999999;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
        }

        #ai-widget-toggle {
          width: 60px;
          height: 60px;
          border-radius: 50%;
          background-color: ${this.config.primaryColor};
          color: white;
          border: none;
          cursor: pointer;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 24px;
          transition: transform 0.2s, box-shadow 0.2s;
        }

        #ai-widget-toggle:hover {
          transform: scale(1.05);
          box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
        }

        #ai-widget-chat {
          position: absolute;
          bottom: 80px;
          ${this.config.position === "bottom-left" ? "left" : "right"}: 0;
          width: 380px;
          max-width: calc(100vw - 40px);
          height: 550px;
          background: white;
          border-radius: 16px;
          box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
          display: none;
          flex-direction: column;
          overflow: hidden;
        }

        #ai-widget-chat.open {
          display: flex;
          animation: slideUp 0.3s ease-out;
        }

        @keyframes slideUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        #ai-widget-header {
          background-color: ${this.config.primaryColor};
          color: white;
          padding: 20px;
          display: flex;
          align-items: center;
          gap: 12px;
        }

        #ai-widget-avatar {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          background-color: rgba(255, 255, 255, 0.2);
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 600;
        }

        #ai-widget-title {
          flex: 1;
        }

        #ai-widget-title-text {
          font-weight: 600;
          font-size: 16px;
          margin: 0;
        }

        #ai-widget-subtitle {
          font-size: 13px;
          opacity: 0.9;
          margin: 2px 0 0 0;
        }

        #ai-widget-close {
          background: none;
          border: none;
          color: white;
          font-size: 24px;
          cursor: pointer;
          padding: 0;
          width: 32px;
          height: 32px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 50%;
          transition: background-color 0.2s;
        }

        #ai-widget-close:hover {
          background-color: rgba(255, 255, 255, 0.1);
        }

        #ai-widget-messages {
          flex: 1;
          overflow-y: auto;
          padding: 20px;
          background: #f9fafb;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .ai-widget-message {
          display: flex;
          gap: 8px;
          max-width: 80%;
          animation: fadeIn 0.3s ease-out;
        }

        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .ai-widget-message.user {
          align-self: flex-end;
          flex-direction: row-reverse;
        }

        .ai-widget-message-avatar {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          background-color: #e5e7eb;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 12px;
          font-weight: 600;
          flex-shrink: 0;
        }

        .ai-widget-message.user .ai-widget-message-avatar {
          background-color: ${this.config.primaryColor};
          color: white;
        }

        .ai-widget-message-content {
          background: white;
          padding: 10px 14px;
          border-radius: 12px;
          font-size: 14px;
          line-height: 1.5;
          box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
        }

        .ai-widget-message.user .ai-widget-message-content {
          background-color: ${this.config.primaryColor};
          color: white;
        }

        .ai-widget-typing {
          display: flex;
          gap: 4px;
          padding: 10px 14px;
        }

        .ai-widget-typing span {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background-color: #9ca3af;
          animation: typing 1.4s infinite;
        }

        .ai-widget-typing span:nth-child(2) {
          animation-delay: 0.2s;
        }

        .ai-widget-typing span:nth-child(3) {
          animation-delay: 0.4s;
        }

        @keyframes typing {
          0%, 60%, 100% {
            transform: translateY(0);
          }
          30% {
            transform: translateY(-10px);
          }
        }

        #ai-widget-input-container {
          padding: 16px;
          background: white;
          border-top: 1px solid #e5e7eb;
        }

        #ai-widget-input-wrapper {
          display: flex;
          gap: 8px;
        }

        #ai-widget-input {
          flex: 1;
          padding: 10px 14px;
          border: 1px solid #d1d5db;
          border-radius: 8px;
          font-size: 14px;
          outline: none;
          transition: border-color 0.2s;
        }

        #ai-widget-input:focus {
          border-color: ${this.config.primaryColor};
        }

        #ai-widget-send {
          padding: 10px 16px;
          background-color: ${this.config.primaryColor};
          color: white;
          border: none;
          border-radius: 8px;
          cursor: pointer;
          font-size: 14px;
          font-weight: 500;
          transition: opacity 0.2s;
        }

        #ai-widget-send:hover {
          opacity: 0.9;
        }

        #ai-widget-send:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        #ai-widget-branding {
          padding: 8px 16px;
          text-align: center;
          font-size: 11px;
          color: #9ca3af;
          background: white;
        }

        #ai-widget-branding a {
          color: ${this.config.primaryColor};
          text-decoration: none;
        }

        @media (max-width: 640px) {
          #ai-widget-chat {
            width: calc(100vw - 40px);
            height: calc(100vh - 100px);
          }
        }
      `;
      document.head.appendChild(style);
    }

    createWidget() {
      const container = document.createElement("div");
      container.id = "ai-widget-container";
      container.innerHTML = `
        <button id="ai-widget-toggle" aria-label="Open chat">
          💬
        </button>
        <div id="ai-widget-chat">
          <div id="ai-widget-header">
            <div id="ai-widget-avatar">AI</div>
            <div id="ai-widget-title">
              <p id="ai-widget-title-text">${this.config.title}</p>
              <p id="ai-widget-subtitle">${this.config.subtitle}</p>
            </div>
            <button id="ai-widget-close" aria-label="Close chat">×</button>
          </div>
          <div id="ai-widget-messages">
            <div class="ai-widget-message">
              <div class="ai-widget-message-avatar">AI</div>
              <div class="ai-widget-message-content">
                Bonjour ! 👋 Comment puis-je vous aider aujourd'hui ?
              </div>
            </div>
          </div>
          <div id="ai-widget-input-container">
            <div id="ai-widget-input-wrapper">
              <input
                id="ai-widget-input"
                type="text"
                placeholder="Tapez votre message..."
                aria-label="Message input"
              />
              <button id="ai-widget-send">Envoyer</button>
            </div>
          </div>
          ${
            this.config.showBranding
              ? '<div id="ai-widget-branding">Propulsé par <a href="#" target="_blank">AI Support</a></div>'
              : ""
          }
        </div>
      `;

      document.body.appendChild(container);
      this.elements = {
        toggle: container.querySelector("#ai-widget-toggle"),
        chat: container.querySelector("#ai-widget-chat"),
        close: container.querySelector("#ai-widget-close"),
        messages: container.querySelector("#ai-widget-messages"),
        input: container.querySelector("#ai-widget-input"),
        send: container.querySelector("#ai-widget-send"),
      };
    }

    setupEventListeners() {
      this.elements.toggle.addEventListener("click", () => this.toggleChat());
      this.elements.close.addEventListener("click", () => this.closeChat());
      this.elements.send.addEventListener("click", () => this.sendMessage());
      this.elements.input.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
          this.sendMessage();
        }
      });
    }

    toggleChat() {
      if (this.isOpen) {
        this.closeChat();
      } else {
        this.openChat();
      }
    }

    openChat() {
      this.isOpen = true;
      this.elements.chat.classList.add("open");
      this.elements.input.focus();
    }

    closeChat() {
      this.isOpen = false;
      this.elements.chat.classList.remove("open");
    }

    async sendMessage() {
      const message = this.elements.input.value.trim();
      if (!message) return;

      this.addMessage(message, "user");
      this.elements.input.value = "";

      this.showTyping();

      try {
        const response = await fetch(`${this.config.baseUrl}/api/v1/playground/message`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            content: message,
            conversation_id: this.conversationId,
          }),
        });

        this.hideTyping();

        if (!response.ok) {
          throw new Error("Failed to send message");
        }

        const data = await response.json();
        if (data.conversation_id) {
          this.conversationId = data.conversation_id;
        }
        this.addMessage(data.response || "Désolé, je n'ai pas pu traiter cela.", "assistant");
      } catch (error) {
        console.error("Error sending message:", error);
        this.hideTyping();
        this.addMessage(
          "Désolé, j'ai des problèmes de connexion. Veuillez réessayer plus tard.",
          "assistant"
        );
      }
    }

    addMessage(content, role) {
      const messageDiv = document.createElement("div");
      messageDiv.className = `ai-widget-message ${role}`;
      messageDiv.innerHTML = `
        <div class="ai-widget-message-avatar">${role === "user" ? "U" : "AI"}</div>
        <div class="ai-widget-message-content">${this.escapeHtml(content)}</div>
      `;

      this.elements.messages.appendChild(messageDiv);
      this.scrollToBottom();
    }

    showTyping() {
      const typingDiv = document.createElement("div");
      typingDiv.className = "ai-widget-message";
      typingDiv.id = "ai-widget-typing-indicator";
      typingDiv.innerHTML = `
        <div class="ai-widget-message-avatar">AI</div>
        <div class="ai-widget-message-content">
          <div class="ai-widget-typing">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      `;
      this.elements.messages.appendChild(typingDiv);
      this.scrollToBottom();
    }

    hideTyping() {
      const typingIndicator = document.getElementById("ai-widget-typing-indicator");
      if (typingIndicator) {
        typingIndicator.remove();
      }
    }

    scrollToBottom() {
      this.elements.messages.scrollTop = this.elements.messages.scrollHeight;
    }

    escapeHtml(text) {
      const div = document.createElement("div");
      div.textContent = text;
      return div.innerHTML;
    }
  }

  window.AISupportWidget = {
    init: function (config) {
      if (!config.apiKey) {
        console.warn("AI Support Widget: No API key provided");
      }

      new AISupportWidget(config);
    },
  };
})();

