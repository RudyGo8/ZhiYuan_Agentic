(function bootstrapAuthFeature(global) {
    global.AppModules = global.AppModules || {};

    function createAuthMethods(config) {
        return {
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
            }
        };
    }

    global.AppModules.createAuthMethods = createAuthMethods;
})(window);
