(function bootstrapMarkdown(global) {
    global.AppModules = global.AppModules || {};

    function configureMarkdown() {
        marked.setOptions({
            highlight(code, lang) {
                const language = hljs.getLanguage(lang) ? lang : 'plaintext';
                return hljs.highlight(code, { language }).value;
            },
            langPrefix: 'hljs language-',
            breaks: true,
            gfm: true
        });
    }

    function sanitizeHtml(html) {
        if (global.DOMPurify) {
            return global.DOMPurify.sanitize(html, {
                USE_PROFILES: { html: true }
            });
        }
        return html;
    }

    function renderMarkdown(text) {
        const rawHtml = marked.parse(text || '');
        return sanitizeHtml(rawHtml);
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }

    global.AppModules.configureMarkdown = configureMarkdown;
    global.AppModules.renderMarkdown = renderMarkdown;
    global.AppModules.escapeHtml = escapeHtml;
})(window);
