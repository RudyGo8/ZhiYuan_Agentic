(function bootstrapConfig(global) {
    global.AppModules = global.AppModules || {};

    global.AppModules.config = Object.freeze({
        BASE_URL: '/api/r1',
        TOKEN_STORAGE_KEY: 'accessToken',
        THEME_STORAGE_KEY: 'zhiyuan-theme'
    });
})(window);
