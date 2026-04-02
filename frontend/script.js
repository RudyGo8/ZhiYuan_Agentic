const { createApp } = Vue;

const {
    config,
    createInitialState,
    createApiService,
    configureMarkdown,
    renderMarkdown,
    escapeHtml,
    createAuthMethods,
    createChatMethods,
    createHistoryMethods,
    createDocumentMethods,
    createUiMethods
} = window.AppModules;

const methods = Object.assign(
    {
        parseMarkdown(text) {
            return renderMarkdown(text);
        },
        escapeHtml
    },
    createAuthMethods(config),
    createChatMethods(),
    createHistoryMethods(),
    createDocumentMethods(),
    createUiMethods(config)
);

createApp({
    data() {
        return createInitialState(config);
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
    methods,
    watch: {
        messages: {
            handler() {
                this.$nextTick(() => {
                    this.scrollToBottom();
                });
            },
            deep: true
        }
    }
}).mount('#app');
