<template>
  <div class="app-wrapper">
    <AppSidebar
      :active-nav="activeNav"
      :current-user="currentUser"
      :is-admin="isAdmin"
      :is-authenticated="isAuthenticated"
      @new-chat="handleNewChat"
      @history="handleHistory"
      @settings="handleSettings"
      @clear-chat="handleClearChat"
      @logout="handleLogout"
    />

    <main class="main-content">
      <AuthPanel
        v-if="!isAuthenticated"
        :form="authForm"
        :loading="authLoading"
        :mode="authMode"
        @submit="handleAuthSubmit"
        @switch-mode="toggleAuthMode"
      />

      <DocumentManager
        v-else-if="activeNav === 'settings'"
        :documents="documents"
        :loading="documentsLoading"
        :selected-file="selectedFile"
        :uploading="isUploading"
        :upload-progress="uploadProgress"
        @select-file="handleFileSelect"
        @upload="uploadDocument"
        @refresh="loadDocuments"
        @delete-document="deleteDocument"
      />

      <HistorySidebar
        v-if="isAuthenticated && showHistorySidebar"
        :active-session-id="sessionId"
        :sessions="sessions"
        @close="showHistorySidebar = false"
        @load-session="loadSession"
        @delete-session="deleteSession"
      />

      <div v-show="isAuthenticated && activeNav !== 'settings'" class="chat-area">
        <header class="chat-header">
          <div class="header-info">
            <div class="status-dot"></div>
            <span>知源在线中...</span>
          </div>
          <div class="header-actions">
            <button
              class="icon-btn theme-toggle-btn"
              :title="isDarkMode ? '切换到日间模式' : '切换到夜间模式'"
              @click="toggleTheme"
            >
              <i :class="isDarkMode ? 'fas fa-sun' : 'fas fa-moon'"></i>
            </button>
            <button class="icon-btn" title="更多"><i class="fas fa-ellipsis-h"></i></button>
          </div>
        </header>

        <MessageList :messages="messages" />

        <MessageInput
          v-model="userInput"
          :loading="isLoading"
          @send="handleSend"
          @stop="handleStop"
        />
      </div>
    </main>
  </div>
</template>

<script>
import { config } from '../config';
import { createInitialState } from '../state';
import { createApiService } from '../services/api';
import { configureMarkdown } from '../services/markdown';
import { fetchCurrentUser, login as loginUser, register as registerUser } from '../services/authService';
import { openChatStream } from '../services/chatService';
import { consumeChatStream } from '../services/chatStream';
import { listDocuments, removeDocument, uploadDocumentFile } from '../services/documentService';
import { getSessionMessages, listSessions, removeSession } from '../services/sessionService';
import AppSidebar from '../components/layout/AppSidebar.vue';
import AuthPanel from '../components/auth/AuthPanel.vue';
import DocumentManager from '../components/documents/DocumentManager.vue';
import HistorySidebar from '../components/history/HistorySidebar.vue';
import MessageInput from '../components/chat/MessageInput.vue';
import MessageList from '../components/chat/MessageList.vue';

export default {
  components: {
    AppSidebar,
    AuthPanel,
    DocumentManager,
    HistorySidebar,
    MessageInput,
    MessageList
  },
  data() {
    return {
      ...createInitialState(config),
      api: null
    };
  },
  computed: {
    isAuthenticated() {
      return !!this.token && !!this.currentUser;
    },
    isAdmin() {
      return this.currentUser?.role === 'admin';
    }
  },
  async mounted() {
    configureMarkdown();
    this.api = createApiService(config.BASE_URL);
    this.applyTheme();
    await this.restoreAuth();
  },
  methods: {
    async restoreAuth() {
      if (!this.token) return;
      try {
        await this.fetchMe();
      } catch (_) {
        this.handleLogout();
      }
    },
    handleServiceError(error) {
      if (error?.status === 401) {
        this.handleLogout();
      }
      return error?.message || '请求失败';
    },
    applyTheme() {
      document.body.classList.toggle('theme-dark', this.isDarkMode);
    },
    toggleTheme() {
      this.isDarkMode = !this.isDarkMode;
      localStorage.setItem(config.THEME_STORAGE_KEY, this.isDarkMode ? 'dark' : 'light');
      this.applyTheme();
    },
    toggleAuthMode() {
      this.authMode = this.authMode === 'login' ? 'register' : 'login';
    },
    async fetchMe() {
      this.currentUser = await fetchCurrentUser(this.api, this.token);
    },
    async handleAuthSubmit() {
      if (this.authLoading) return;

      const username = this.authForm.username.trim();
      const password = this.authForm.password.trim();
      if (!username || !password) {
        alert('用户名和密码不能为空');
        return;
      }

      this.authLoading = true;
      try {
        const payload = { username, password };
        const data = this.authMode === 'register'
          ? await registerUser(this.api, {
            ...payload,
            role: this.authForm.role,
            admin_code: this.authForm.admin_code || null
          })
          : await loginUser(this.api, payload);

        this.token = data.access_token;
        this.currentUser = { username: data.username, role: data.role };
        localStorage.setItem(config.TOKEN_STORAGE_KEY, this.token);
        this.authForm.password = '';
        this.authForm.admin_code = '';
        this.messages = [];
        this.sessionId = `session_${Date.now()}`;
        this.activeNav = 'newChat';
      } catch (error) {
        alert(this.handleServiceError(error));
      } finally {
        this.authLoading = false;
      }
    },
    handleLogout() {
      this.token = '';
      this.currentUser = null;
      this.messages = [];
      this.sessions = [];
      this.documents = [];
      this.activeNav = 'newChat';
      this.showHistorySidebar = false;
      localStorage.removeItem(config.TOKEN_STORAGE_KEY);
    },
    handleStop() {
      this.abortController?.abort();
    },
    appendRagStep(message, step) {
      if (!message || !Array.isArray(message.ragSteps) || !step) return;

      const icon = step.icon || '';
      const label = step.label || '';
      const detail = step.detail || '';

      if (label.includes('查询外部来源')) return;

      const signature = `${icon}|${label}|${detail}`;
      const last = message.ragSteps.at(-1);
      const lastSignature = last ? `${last.icon || ''}|${last.label || ''}|${last.detail || ''}` : '';

      if (signature !== lastSignature) {
        message.ragSteps.push(step);
      }
    },
    async handleSend() {
      if (!this.isAuthenticated) {
        alert('请先登录');
        return;
      }

      const text = this.userInput.trim();
      if (!text || this.isLoading) return;

      this.messages.push({ text, isUser: true });
      this.userInput = '';
      this.isLoading = true;

      this.messages.push({
        text: '',
        isUser: false,
        isThinking: true,
        ragTrace: null,
        ragSteps: []
      });

      const botMsg = this.messages[this.messages.length - 1];
      this.abortController = new AbortController();

      try {
        const response = await openChatStream(this.api, this.token, {
          message: text,
          sessionId: this.sessionId,
          signal: this.abortController.signal
        });

        if (!response.ok) {
          if (response.status === 401) this.handleLogout();
          throw new Error(`HTTP ${response.status}`);
        }

        await consumeChatStream(response, {
          onContent: (content) => {
            botMsg.isThinking = false;
            botMsg.text += content;
          },
          onTrace: (ragTrace) => {
            botMsg.ragTrace = ragTrace;
          },
          onRagStep: (step) => {
            this.appendRagStep(botMsg, step);
          },
          onError: (errorMsg) => {
            botMsg.isThinking = false;
            botMsg.text += `\n[Error: ${errorMsg}]`;
          },
          onDone: () => {
            botMsg.isThinking = false;
          },
          onParseError: (error) => {
            console.warn('SSE parse error:', error);
          }
        });
      } catch (error) {
        botMsg.isThinking = false;
        if (error.name === 'AbortError') {
          botMsg.text = botMsg.text
            ? `${botMsg.text}\n\n_(回答已被终止)_`
            : '(已终止回答)';
        } else {
          botMsg.text = `Sorry... 出了点问题：${error.message}`;
        }
      } finally {
        this.isLoading = false;
        this.abortController = null;
      }
    },
    handleNewChat() {
      if (!this.isAuthenticated) return;
      this.messages = [];
      this.sessionId = `session_${Date.now()}`;
      this.activeNav = 'newChat';
      this.showHistorySidebar = false;
    },
    handleClearChat() {
      if (confirm('确定要清空当前对话吗？')) {
        this.messages = [];
      }
    },
    async handleHistory() {
      if (!this.isAuthenticated) return;
      this.activeNav = 'history';
      this.showHistorySidebar = true;

      try {
        this.sessions = await listSessions(this.api, this.token);
      } catch (error) {
        alert(`加载历史记录失败：${this.handleServiceError(error)}`);
      }
    },
    async loadSession(sessionId) {
      this.sessionId = sessionId;
      this.showHistorySidebar = false;
      this.activeNav = 'newChat';

      try {
        const messages = await getSessionMessages(this.api, this.token, sessionId);
        this.messages = messages.map((msg) => ({
          text: msg.content,
          isUser: msg.type === 'human',
          ragTrace: msg.rag_trace || null,
          ragSteps: []
        }));
      } catch (error) {
        alert(`加载会话失败：${this.handleServiceError(error)}`);
        this.messages = [];
      }
    },
    async deleteSession(sessionId) {
      if (!confirm(`确定要删除会话 "${sessionId}" 吗？`)) return;

      try {
        const payload = await removeSession(this.api, this.token, sessionId);
        this.sessions = this.sessions.filter((item) => item.session_id !== sessionId);
        if (this.sessionId === sessionId) {
          this.messages = [];
          this.sessionId = `session_${Date.now()}`;
          this.activeNav = 'newChat';
        }
        if (payload.message) alert(payload.message);
      } catch (error) {
        alert(`删除会话失败：${this.handleServiceError(error)}`);
      }
    },
    handleSettings() {
      if (!this.isAdmin) {
        alert('仅管理员可访问文档管理');
        return;
      }
      this.activeNav = 'settings';
      this.showHistorySidebar = false;
      this.loadDocuments();
    },
    async loadDocuments() {
      this.documentsLoading = true;
      try {
        this.documents = await listDocuments(this.api, this.token);
      } catch (error) {
        alert(`加载文档列表失败：${this.handleServiceError(error)}`);
      } finally {
        this.documentsLoading = false;
      }
    },
    handleFileSelect(file) {
      this.selectedFile = file;
      this.uploadProgress = '';
    },
    async uploadDocument() {
      if (!this.selectedFile) {
        alert('请先选择文件');
        return;
      }

      this.isUploading = true;
      this.uploadProgress = '正在上传...';
      try {
        const data = await uploadDocumentFile(this.api, this.token, this.selectedFile);
        this.uploadProgress = data.message;
        this.selectedFile = null;
        await this.loadDocuments();
        setTimeout(() => {
          this.uploadProgress = '';
        }, 3000);
      } catch (error) {
        this.uploadProgress = `上传失败：${this.handleServiceError(error)}`;
      } finally {
        this.isUploading = false;
      }
    },
    async deleteDocument(filename) {
      if (!confirm(`确定要删除文档 "${filename}" 吗？这会同时删除 Milvus 中的相关向量。`)) return;

      try {
        const data = await removeDocument(this.api, this.token, filename);
        alert(data.message);
        await this.loadDocuments();
      } catch (error) {
        alert(`删除文档失败：${this.handleServiceError(error)}`);
      }
    }
  }
};
</script>
