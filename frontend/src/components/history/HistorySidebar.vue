<template>
  <div class="history-sidebar">
    <div class="history-header">
      <h3>历史会话</h3>
      <button @click="$emit('close')" class="close-btn">
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
        :class="{ active: session.session_id === activeSessionId }"
      >
        <div class="session-body" @click="$emit('load-session', session.session_id)">
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
          @click.stop="$emit('delete-session', session.session_id)"
        >
          <i class="fas fa-trash"></i>
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    activeSessionId: {
      type: String,
      required: true
    },
    sessions: {
      type: Array,
      default: () => []
    }
  },
  emits: ['close', 'load-session', 'delete-session']
};
</script>
