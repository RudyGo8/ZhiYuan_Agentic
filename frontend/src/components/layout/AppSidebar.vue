<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="logo-icon">知</div>
    </div>

    <nav class="sidebar-nav">
      <button @click="$emit('new-chat')" :class="['nav-btn', { active: activeNav === 'newChat' }]">
        <i class="fas fa-plus"></i> 新建会话
      </button>
      <button @click="$emit('history')" :class="['nav-btn', { active: activeNav === 'history' }]">
        <i class="fas fa-history"></i> 历史记录
      </button>
      <button v-if="isAdmin" @click="$emit('settings')" :class="['nav-btn', { active: activeNav === 'settings' }]">
        <i class="fas fa-cog"></i> 设置
      </button>
    </nav>

    <div class="sidebar-footer">
      <button @click="$emit('clear-chat')" class="danger-btn">
        <i class="fas fa-trash-alt"></i> 清空对话
      </button>
      <div v-if="isAuthenticated" class="user-badge">
        <span>{{ currentUser.username }}</span>
        <small>{{ currentUser.role }}</small>
      </div>
      <button v-if="isAuthenticated" @click="$emit('logout')" class="danger-btn logout-btn">
        <i class="fas fa-right-from-bracket"></i> 退出登录
      </button>
    </div>
  </aside>
</template>

<script>
export default {
  props: {
    activeNav: {
      type: String,
      required: true
    },
    currentUser: {
      type: Object,
      default: null
    },
    isAdmin: {
      type: Boolean,
      default: false
    },
    isAuthenticated: {
      type: Boolean,
      default: false
    }
  },
  emits: ['new-chat', 'history', 'settings', 'clear-chat', 'logout']
};
</script>
