(function bootstrapHistoryFeature(global) {
    global.AppModules = global.AppModules || {};

    function createHistoryMethods() {
        return {
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
            }
        };
    }

    global.AppModules.createHistoryMethods = createHistoryMethods;
})(window);
