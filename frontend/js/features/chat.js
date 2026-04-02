(function bootstrapChatFeature(global) {
    global.AppModules = global.AppModules || {};

    function createChatMethods() {
        return {
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

                this.messages.push({
                    text,
                    isUser: true
                });

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

                            if (!eventStr.startsWith('data: ')) {
                                continue;
                            }

                            const dataStr = eventStr.slice(6);
                            if (dataStr === '[DONE]') {
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
                                    this.messages[botMsgIdx].ragSteps.push(data.step);
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
            }
        };
    }

    global.AppModules.createChatMethods = createChatMethods;
})(window);
