<template>
  <div :class="['message', message.isUser ? 'user-message' : 'bot-message']">
    <div v-if="showThinking" class="message-content thinking-content">
      <div class="thinking-header">
        <div class="thinking-dots">
          <span class="tdot"></span>
          <span class="tdot"></span>
          <span class="tdot"></span>
        </div>
        <span v-if="!message.ragSteps || !message.ragSteps.length" class="thinking-text">正在思考中...</span>
        <span v-else class="thinking-text">{{ message.ragSteps[message.ragSteps.length - 1].label }}</span>
      </div>

      <div v-if="message.ragSteps && message.ragSteps.length" class="thinking-trace-lines">
        <div v-for="(step, index) in message.ragSteps" :key="index" class="thinking-trace-line">
          <span class="thinking-trace-icon">{{ step.icon || '•' }}</span>
          <span class="thinking-trace-label">{{ step.label }}</span>
          <span v-if="step.detail" class="thinking-trace-detail">{{ step.detail }}</span>
        </div>
      </div>
    </div>

    <div v-if="showStepTags" class="rag-steps-display">
      <span v-for="(step, index) in message.ragSteps" :key="index" class="rag-step-tag">
        {{ step.icon || '•' }} {{ step.label }}
      </span>
    </div>

    <div class="message-content" v-html="renderedContent"></div>

    <div v-if="!message.isUser && message.ragTrace" class="message-meta">
      <details class="reasoning-details">
        <summary>检索过程</summary>
        <div class="reasoning-content">
          <div class="trace-line">
            RAG 工具：{{ message.ragTrace.tool_used ? message.ragTrace.tool_name : '未使用' }}
          </div>
          <div v-if="message.ragTrace.retrieval_stage" class="trace-line">
            检索阶段：{{ message.ragTrace.retrieval_stage }}
          </div>
          <div v-if="message.ragTrace.grade_score" class="trace-line">
            相关性评分：{{ message.ragTrace.grade_score }}
          </div>
          <div v-if="message.ragTrace.skill?.display_name" class="trace-line">
            Skill：{{ message.ragTrace.skill.display_name }}
          </div>
          <div v-if="Array.isArray(message.ragTrace.mcp_calls)" class="trace-line">
            MCP 调用：{{ formatMcpCallSummary(message.ragTrace) }}
          </div>
        </div>
      </details>
    </div>
  </div>
</template>

<script>
import { escapeHtml, renderMarkdown } from '../../services/markdown';

export default {
  props: {
    message: {
      type: Object,
      required: true
    }
  },
  computed: {
    showThinking() {
      return !this.message.isUser && this.message.isThinking && !this.message.text;
    },
    showStepTags() {
      return !this.message.isUser
        && this.message.ragSteps
        && this.message.ragSteps.length
        && (!this.message.isThinking || this.message.text);
    },
    renderedContent() {
      return this.message.isUser ? escapeHtml(this.message.text) : renderMarkdown(this.message.text);
    }
  },
  methods: {
    formatMcpCallSummary(ragTrace) {
      const calls = Array.isArray(ragTrace?.mcp_calls) ? ragTrace.mcp_calls : [];
      const successCalls = calls.filter((item) => item && item.success === true);
      if (successCalls.length === 0) return '未调用';

      const sourceCount = new Map();
      for (const item of successCalls) {
        const source = (item.server_name || '').trim();
        if (!source) continue;
        sourceCount.set(source, (sourceCount.get(source) || 0) + 1);
      }

      if (sourceCount.size === 0) {
        return `${successCalls.length} 次`;
      }

      const sourceText = Array.from(sourceCount.entries())
        .map(([source, count]) => `${source}${count > 1 ? `x${count}` : ''}`)
        .join('、');

      return `${sourceText}（${successCalls.length} 次）`;
    }
  }
};
</script>
