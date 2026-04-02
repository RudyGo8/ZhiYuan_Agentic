import { marked } from 'marked';
import hljs from 'highlight.js';
import DOMPurify from 'dompurify';

export function configureMarkdown() {
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

export function renderMarkdown(text) {
  const rawHtml = marked.parse(text || '');
  return DOMPurify.sanitize(rawHtml, { USE_PROFILES: { html: true } });
}

export function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}
