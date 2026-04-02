(function bootstrapUiFeature(global) {
    global.AppModules = global.AppModules || {};

    function createUiMethods(config) {
        return {
            applyTheme() {
                document.body.classList.toggle('theme-dark', this.isDarkMode);
            },

            toggleTheme() {
                this.isDarkMode = !this.isDarkMode;
                localStorage.setItem(config.THEME_STORAGE_KEY, this.isDarkMode ? 'dark' : 'light');
                this.applyTheme();
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

            getFileIcon(fileType) {
                if (fileType === 'PDF') return 'fas fa-file-pdf';
                if (fileType === 'Word') return 'fas fa-file-word';
                if (fileType === 'Excel') return 'fas fa-file-excel';
                return 'fas fa-file';
            }
        };
    }

    global.AppModules.createUiMethods = createUiMethods;
})(window);
