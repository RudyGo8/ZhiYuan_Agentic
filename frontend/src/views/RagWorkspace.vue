<template>
  <div class="app-wrapper">
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="logo-icon">🤖</div>
      </div>
      <nav class="sidebar-nav">
        <button @click="handleNewChat" :class="['nav-btn', { active: activeNav === 'newChat' }]">
          <i class="fas fa-plus"></i> 新建会话
        </button>
        <button @click="handleHistory" :class="['nav-btn', { active: activeNav === 'history' }]">
          <i class="fas fa-history"></i> 历史记录
        </button>
        <button v-if="isAdmin" @click="handleSettings" :class="['nav-btn', { active: activeNav === 'settings' }]">
          <i class="fas fa-cog"></i> 设置
        </button>
      </nav>
      <div class="sidebar-footer">
        <button @click="handleClearChat" class="danger-btn">
          <i class="fas fa-trash-alt"></i> 清空对话
        </button>
        <div v-if="isAuthenticated" class="user-badge">
          <span>{{ currentUser.username }}</span>
          <small>{{ currentUser.role }}</small>
        </div>
        <button v-if="isAuthenticated" @click="handleLogout" class="danger-btn logout-btn">
          <i class="fas fa-right-from-bracket"></i> 退出登录
        </button>
      </div>
    </aside>

    <main class="main-content">
      <div v-if="!isAuthenticated" class="auth-panel">
        <h2>{{ authMode === 'login' ? '登录知源' : '注册知源' }}</h2>
        <p>登录后即可使用聊天和历史记录；管理员可管理文档知识库。</p>
        <div class="auth-form">
          <input v-model="authForm.username" type="text" placeholder="用户名" />
          <input v-model="authForm.password" type="password" placeholder="密码" />
          <select v-if="authMode === 'register'" v-model="authForm.role">
            <option value="user">普通用户</option>
            <option value="admin">管理员</option>
          </select>
          <input v-if="authMode === 'register' && authForm.role === 'admin'" v-model="authForm.admin_code" type="password" placeholder="管理员邀请码" />
          <button class="send-btn auth-submit" :disabled="authLoading" @click="handleAuthSubmit">
            {{ authLoading ? '提交中...' : (authMode === 'login' ? '登录' : '注册') }}
          </button>
          <button class="auth-switch" @click="authMode = authMode === 'login' ? 'register' : 'login'">
            {{ authMode === 'login' ? '没有账号？去注册' : '已有账号？去登录' }}
          </button>
        </div>
      </div>

      <div v-if="isAuthenticated && activeNav === 'settings'" class="settings-panel">
        <div class="settings-header">
          <h2><i class="fas fa-cog"></i> 文档管理</h2>
          <p>上传文档进行向量化处理，支持 PDF 和 Word、Excel 格式</p>
        </div>

        <div class="upload-section">
          <h3><i class="fas fa-upload"></i> 上传文档</h3>
          <div class="upload-area">
            <input
              type="file"
              ref="fileInput"
              @change="handleFileSelect"
              accept=".pdf,.doc,.docx,.xls,.xlsx"
              style="display: none"
            />
            <button @click="$refs.fileInput.click()" class="upload-btn">
              <i class="fas fa-cloud-upload-alt"></i> 选择文件
            </button>
            <div v-if="selectedFile" class="selected-file">
              <i class="fas fa-file"></i> {{ selectedFile.name }}
              <button @click="uploadDocument" class="btn-primary" :disabled="isUploading">
                <i class="fas fa-upload"></i> {{ isUploading ? '上传中...' : '开始上传' }}
              </button>
            </div>
            <div v-if="uploadProgress" class="upload-progress">
              {{ uploadProgress }}
            </div>
          </div>
        </div>

        <div class="documents-section">
          <h3><i class="fas fa-list"></i> 已上传文档</h3>
          <button @click="loadDocuments" class="btn-secondary">
            <i class="fas fa-sync"></i> 刷新列表
          </button>

          <div v-if="documentsLoading" class="loading-indicator">
            加载中...
          </div>

          <div v-else-if="documents.length === 0" class="empty-documents">
            <i class="fas fa-inbox"></i>
            <p>暂无文档</p>
          </div>

          <div v-else class="documents-list">
            <div
              v-for="doc in documents"
              :key="doc.filename"
              class="document-item"
            >
              <div class="document-info">
                <div class="document-icon">
                  <i :class="getFileIcon(doc.file_type)"></i>
                </div>
                <div class="document-details">
                  <div class="document-name">{{ doc.filename }}</div>
                  <div class="document-meta">
                    <span>{{ doc.file_type }}</span>
                    <span>{{ doc.chunk_count }} 个文本片段</span>
                  </div>
                </div>
              </div>
              <button
                @click="deleteDocument(doc.filename)"
                class="btn-danger"
                title="删除文档"
              >
                <i class="fas fa-trash"></i>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div v-if="isAuthenticated && showHistorySidebar" class="history-sidebar">
        <div class="history-header">
          <h3>历史会话</h3>
          <button @click="showHistorySidebar = false" class="close-btn">
            <i class="fas fa-times"></i>
          </button>
        </div>
        <div class="history-list">
          <div v-if="sessions.length === 0" class="empty-history">
            <p>暂无历史记录</p>
          </div>
          <div
            v-for="session in sessions"
            :key="session.session_id"
            class="history-item"
            :class="{ active: session.session_id === sessionId }"
          >
            <div class="session-body" @click="loadSession(session.session_id)">
              <div class="session-info">
                <div class="session-title">{{ session.session_id }}</div>
                <div class="session-meta">
                  <span>{{ session.message_count }} 条消息</span>
                  <span>{{ new Date(session.updated_at).toLocaleString() }}</span>
                </div>
              </div>
            </div>
            <button
              class="history-delete-btn"
              title="删除会话"
              @click.stop="deleteSession(session.session_id)"
            >
              <i class="fas fa-trash"></i>
            </button>
          </div>
        </div>
      </div>

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

        <div class="chat-container" ref="chatContainer">
          <div v-if="messages.length === 0" class="welcome-screen">
            <div class="big-avatar">🤖</div>
            <h3>你好，我是知源助手</h3>
            <p>我可以基于知识库回答问题、梳理资料、辅助分析，并展示检索依据。</p>
          </div>

          <div v-for="(msg, index) in messages" :key="index" :class="['message', msg.isUser ? 'user-message' : 'bot-message']">
            <div v-if="!msg.isUser && msg.isThinking && !msg.text" class="message-content thinking-content">
              <div class="thinking-header">
                <div class="thinking-dots">
                  <span class="tdot"></span>
                  <span class="tdot"></span>
                  <span class="tdot"></span>
                </div>
                <span v-if="!msg.ragSteps || !msg.ragSteps.length" class="thinking-text">正在思考中...</span>
                <span v-else class="thinking-text">{{ msg.ragSteps[msg.ragSteps.length - 1].label }}</span>
              </div>
              <div v-if="msg.ragSteps && msg.ragSteps.length" class="thinking-trace-lines">
                <div v-for="(step, sIdx) in msg.ragSteps" :key="sIdx" class="thinking-trace-line">
                  <span class="thinking-trace-icon">{{ step.icon || '▶' }}</span>
                  <span class="thinking-trace-label">{{ step.label }}</span>
                  <span v-if="step.detail" class="thinking-trace-detail">{{ step.detail }}</span>
                </div>
              </div>
            </div>

            <div v-if="!msg.isUser && msg.ragSteps && msg.ragSteps.length && (!msg.isThinking || msg.text)" class="rag-steps-display">
              <span v-for="(step, sIdx) in msg.ragSteps" :key="sIdx" class="rag-step-tag">
                {{ step.icon || '▶' }} {{ step.label }}
              </span>
            </div>

            <div class="message-content" v-html="msg.isUser ? escapeHtml(msg.text) : parseMarkdown(msg.text)"></div>

            <div v-if="!msg.isUser && msg.ragTrace" class="message-meta">
              <details class="reasoning-details">
                <summary>检索过程</summary>
                <div class="reasoning-content">
                  <div class="trace-line">
                    RAG工具：{{ msg.ragTrace.tool_used ? msg.ragTrace.tool_name : '未使用' }}
                  </div>
                  <div v-if="msg.ragTrace.retrieval_stage" class="trace-line">
                    检索阶段：{{ msg.ragTrace.retrieval_stage }}
                  </div>
                  <div v-if="msg.ragTrace.grade_score" class="trace-line">
                    相关性评分：{{ msg.ragTrace.grade_score }}
                  </div>
                  <div v-if="msg.ragTrace.skill?.display_name" class="trace-line">
                    Skill：{{ msg.ragTrace.skill.display_name }}
                  </div>
                  <div v-if="Array.isArray(msg.ragTrace.mcp_calls)" class="trace-line">
                    MCP 调用：{{ formatMcpCallSummary(msg.ragTrace) }}
                  </div>
                </div>
              </details>
            </div>
          </div>
        </div>

        <div class="input-area-wrapper">
          <div class="input-area">
            <button class="attach-btn"><i class="fas fa-paperclip"></i></button>
            <textarea
              v-model="userInput"
              @keydown="handleKeyDown"
              @compositionstart="handleCompositionStart"
              @compositionend="handleCompositionEnd"
              @input="autoResize"
              placeholder="和知源说点什么吧... (Shift+Enter 换行)"
              rows="1"
              ref="textarea"
            ></textarea>
            <button v-if="isLoading" @click="handleStop" class="send-btn stop-btn" title="终止回答">
              <i class="fas fa-stop"></i>
            </button>
            <button v-else @click="handleSend" class="send-btn" title="发送">
              <i class="fas fa-paper-plane"></i>
            </button>
          </div>
          <div class="footer-text">知源助手会尽量基于知识库生成回答，生成内容仍可能存在偏差，请仔细甄别。</div>
        </div>
      </div>
    </main>
  </div>
</template>

<script>
import { config } from '../config';
import { createInitialState } from '../state';
import { createApiService } from '../services/api';
import { configureMarkdown, renderMarkdown, escapeHtml } from '../services/markdown';

export default {
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
    if (this.token) {
      try {
        await this.fetchMe();
      } catch (_) {
        this.handleLogout();
      }
    }
  },
  methods: {
    parseMarkdown(text) {
      return renderMarkdown(text);
    },
    escapeHtml,
    appendRagStep(message, step) {
      if (!message || !Array.isArray(message.ragSteps) || !step || typeof step !== 'object') {
        return;
      }

      const icon = step.icon || '';
      const label = step.label || '';
      const detail = step.detail || '';
      const signature = `${icon}|${label}|${detail}`;
      const isSourceStep = label.includes('查询外部来源');

      if (isSourceStep) {
        // Hide intermediate source-query progress; keep final MCP summary in trace only.
        return;
      }

      const last = message.ragSteps.length ? message.ragSteps[message.ragSteps.length - 1] : null;
      if (last) {
        const li = last.icon || '';
        const ll = last.label || '';
        const ld = last.detail || '';
        if (`${li}|${ll}|${ld}` === signature) return;
      }

      message.ragSteps.push(step);
    },
    formatMcpCallSummary(ragTrace) {
      const calls = Array.isArray(ragTrace?.mcp_calls) ? ragTrace.mcp_calls : [];
      const successCalls = calls.filter((item) => item && item.success === true);
      const total = successCalls.length;
      if (total === 0) {
        return '未调用';
      }

      const sourceCounter = new Map();
      for (const item of successCalls) {
        const source = (item?.server_name || '').trim();
        if (!source) continue;
        sourceCounter.set(source, (sourceCounter.get(source) || 0) + 1);
      }

      let sourceText = '';
      if (sourceCounter.size > 0) {
        sourceText = Array.from(sourceCounter.entries())
          .map(([source, count]) => `${source}${count > 1 ? `x${count}` : ''}`)
          .join('、');
      } else {
        const summarySources = Array.isArray(ragTrace?.mcp_summary?.sources) ? ragTrace.mcp_summary.sources : [];
        sourceText = summarySources.length ? summarySources.join('、') : '未记录来源';
      }

      return `${sourceText}（${total} 次）`;
    },
    applyTheme() {
      document.body.classList.toggle('theme-dark', this.isDarkMode);
    },
    toggleTheme() {
      this.isDarkMode = !this.isDarkMode;
      localStorage.setItem(config.THEME_STORAGE_KEY, this.isDarkMode ? 'dark' : 'light');
      this.applyTheme();
    },
    async authFetch(path, options = {}) {
      const response = await this.api.request(path, {
        ...options,
        token: this.token
      });
      if (response.status === 401) {
        this.handleLogout();
        throw new Error('登录已过期，请重新登录');
      }
      return response;
    },
    async fetchMe() {
      const response = await this.authFetch('/auth/me');
      if (!response.ok) {
        throw new Error('认证失败');
      }
      this.currentUser = await response.json();
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
        const endpoint = this.authMode === 'login' ? '/auth/login' : '/auth/register';
        const payload = { username, password };
        if (this.authMode === 'register') {
          payload.role = this.authForm.role;
          payload.admin_code = this.authForm.admin_code || null;
        }
        const { response, data } = await this.api.requestJson(endpoint, {
          method: 'POST',
          body: payload
        });
        if (!response.ok) {
          throw new Error(data.detail || '认证失败');
        }
        this.token = data.access_token;
        this.currentUser = { username: data.username, role: data.role };
        localStorage.setItem(config.TOKEN_STORAGE_KEY, this.token);
        this.authForm.password = '';
        this.authForm.admin_code = '';
        this.messages = [];
        this.sessionId = `session_${Date.now()}`;
        this.activeNav = 'newChat';
      } catch (error) {
        alert(error.message);
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
    handleCompositionStart() {
      this.isComposing = true;
    },
    handleCompositionEnd() {
      this.isComposing = false;
    },
    handleKeyDown(event) {
      if (event.key === 'Enter' && !event.shiftKey && !this.isComposing) {
        event.preventDefault();
        this.handleSend();
      }
    },
    handleStop() {
      if (this.abortController) {
        this.abortController.abort();
      }
    },
    async handleSend() {
      if (!this.isAuthenticated) {
        alert('请先登录');
        return;
      }

      const text = this.userInput.trim();
      if (!text || this.isLoading || this.isComposing) return;

      this.messages.push({ text, isUser: true });
      this.userInput = '';
      this.$nextTick(() => {
        this.resetTextareaHeight();
        this.scrollToBottom();
      });

      this.isLoading = true;
      this.messages.push({
        text: '',
        isUser: false,
        isThinking: true,
        ragTrace: null,
        ragSteps: []
      });
      const botMsgIdx = this.messages.length - 1;
      this.abortController = new AbortController();

      try {
        const response = await this.authFetch('/chat/stream', {
          method: 'POST',
          body: {
            message: text,
            session_id: this.sessionId
          },
          signal: this.abortController.signal
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          let eventEndIndex = buffer.indexOf('\n\n');
          while (eventEndIndex !== -1) {
            const eventStr = buffer.slice(0, eventEndIndex);
            buffer = buffer.slice(eventEndIndex + 2);
            eventEndIndex = buffer.indexOf('\n\n');

            if (!eventStr.startsWith('data: ')) continue;
            const dataStr = eventStr.slice(6);
            if (dataStr === '[DONE]') {
              if (this.messages[botMsgIdx]?.isThinking) {
                this.messages[botMsgIdx].isThinking = false;
              }
              continue;
            }

            try {
              const data = JSON.parse(dataStr);
              if (data.type === 'content') {
                if (this.messages[botMsgIdx].isThinking) {
                  this.messages[botMsgIdx].isThinking = false;
                }
                this.messages[botMsgIdx].text += data.content;
              } else if (data.type === 'trace') {
                this.messages[botMsgIdx].ragTrace = data.rag_trace;
              } else if (data.type === 'rag_step') {
                this.appendRagStep(this.messages[botMsgIdx], data.step);
              } else if (data.type === 'error') {
                this.messages[botMsgIdx].isThinking = false;
                const errorMsg = data.error || data.content || '未知错误';
                this.messages[botMsgIdx].text += `\n[Error: ${errorMsg}]`;
              }
            } catch (parseError) {
              console.warn('SSE parse error:', parseError);
            }
          }
          this.$nextTick(() => this.scrollToBottom());
        }
      } catch (error) {
        if (error.name === 'AbortError') {
          this.messages[botMsgIdx].isThinking = false;
          if (!this.messages[botMsgIdx].text) {
            this.messages[botMsgIdx].text = '(已终止回答)';
          } else {
            this.messages[botMsgIdx].text += '\n\n_(回答已被终止)_';
          }
        } else {
          this.messages[botMsgIdx].isThinking = false;
          this.messages[botMsgIdx].text = `Sorry... 出了点问题：${error.message}`;
        }
      } finally {
        this.isLoading = false;
        this.abortController = null;
        this.$nextTick(() => this.scrollToBottom());
      }
    },
    autoResize(event) {
      const textarea = event.target;
      textarea.style.height = 'auto';
      textarea.style.height = `${textarea.scrollHeight}px`;
    },
    resetTextareaHeight() {
      if (this.$refs.textarea) {
        this.$refs.textarea.style.height = 'auto';
      }
    },
    scrollToBottom() {
      if (this.$refs.chatContainer) {
        this.$refs.chatContainer.scrollTop = this.$refs.chatContainer.scrollHeight;
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
        const response = await this.authFetch('/chat/sessions');
        if (!response.ok) {
          throw new Error('Failed to load sessions');
        }
        const data = await response.json();
        this.sessions = data.sessions;
      } catch (error) {
        alert(`加载历史记录失败：${error.message}`);
      }
    },
    async loadSession(sessionId) {
      this.sessionId = sessionId;
      this.showHistorySidebar = false;
      this.activeNav = 'newChat';
      try {
        const response = await this.authFetch(`/chat/sessions/${encodeURIComponent(sessionId)}`);
        if (!response.ok) {
          throw new Error('Failed to load session messages');
        }
        const data = await response.json();
        this.messages = data.messages.map((msg) => ({
          text: msg.content,
          isUser: msg.type === 'human',
          ragTrace: msg.rag_trace || null
        }));
        this.$nextTick(() => this.scrollToBottom());
      } catch (error) {
        alert(`加载会话失败：${error.message}`);
        this.messages = [];
      }
    },
    async deleteSession(sessionId) {
      if (!confirm(`确定要删除会话 "${sessionId}" 吗？`)) {
        return;
      }

      try {
        const response = await this.authFetch(`/chat/sessions/${encodeURIComponent(sessionId)}`, {
          method: 'DELETE'
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(payload.detail || 'Delete failed');
        }
        this.sessions = this.sessions.filter((s) => s.session_id !== sessionId);
        if (this.sessionId === sessionId) {
          this.messages = [];
          this.sessionId = `session_${Date.now()}`;
          this.activeNav = 'newChat';
        }
        if (payload.message) {
          alert(payload.message);
        }
      } catch (error) {
        alert(`删除会话失败：${error.message}`);
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
        const response = await this.authFetch('/documents');
        if (!response.ok) {
          const data = await response.json().catch(() => ({}));
          throw new Error(data.detail || 'Failed to load documents');
        }
        const data = await response.json();
        this.documents = data.documents;
      } catch (error) {
        alert(`加载文档列表失败：${error.message}`);
      } finally {
        this.documentsLoading = false;
      }
    },
    handleFileSelect(event) {
      const files = event.target.files;
      if (files && files.length > 0) {
        this.selectedFile = files[0];
        this.uploadProgress = '';
      }
    },
    async uploadDocument() {
      if (!this.selectedFile) {
        alert('请先选择文件');
        return;
      }

      this.isUploading = true;
      this.uploadProgress = '正在上传...';
      try {
        const formData = new FormData();
        formData.append('file', this.selectedFile);
        const response = await this.authFetch('/documents/upload', {
          method: 'POST',
          body: formData
        });
        if (!response.ok) {
          const error = await response.json().catch(() => ({}));
          throw new Error(error.detail || 'Upload failed');
        }
        const data = await response.json();
        this.uploadProgress = data.message;
        this.selectedFile = null;
        if (this.$refs.fileInput) {
          this.$refs.fileInput.value = '';
        }
        await this.loadDocuments();
        setTimeout(() => {
          this.uploadProgress = '';
        }, 3000);
      } catch (error) {
        this.uploadProgress = `上传失败：${error.message}`;
      } finally {
        this.isUploading = false;
      }
    },
    async deleteDocument(filename) {
      if (!confirm(`确定要删除文档 "${filename}" 吗？这将同时删除 Milvus 中的所有相关向量。`)) {
        return;
      }

      try {
        const response = await this.authFetch(`/documents/${encodeURIComponent(filename)}`, {
          method: 'DELETE'
        });
        if (!response.ok) {
          const error = await response.json().catch(() => ({}));
          throw new Error(error.detail || 'Delete failed');
        }
        const data = await response.json();
        alert(data.message);
        await this.loadDocuments();
      } catch (error) {
        alert(`删除文档失败：${error.message}`);
      }
    },
    getFileIcon(fileType) {
      if (fileType === 'PDF') return 'fas fa-file-pdf';
      if (fileType === 'Word') return 'fas fa-file-word';
      if (fileType === 'Excel') return 'fas fa-file-excel';
      return 'fas fa-file';
    }
  },
  watch: {
    messages: {
      handler() {
        this.$nextTick(() => this.scrollToBottom());
      },
      deep: true
    }
  }
};
</script>
