<template>
  <div class="auth-panel">
    <h2>{{ mode === 'login' ? '登录知源' : '注册知源' }}</h2>
    <p>登录后即可使用聊天和历史记录；管理员可管理文档知识库。</p>
    <div class="auth-form">
      <input v-model="form.username" type="text" placeholder="用户名" />
      <input v-model="form.password" type="password" placeholder="密码" />
      <select v-if="mode === 'register'" v-model="form.role">
        <option value="user">普通用户</option>
        <option value="admin">管理员</option>
      </select>
      <input
        v-if="mode === 'register' && form.role === 'admin'"
        v-model="form.admin_code"
        type="password"
        placeholder="管理员邀请码"
      />
      <button class="send-btn auth-submit" :disabled="loading" @click="$emit('submit')">
        {{ loading ? '提交中...' : (mode === 'login' ? '登录' : '注册') }}
      </button>
      <button class="auth-switch" @click="$emit('switch-mode')">
        {{ mode === 'login' ? '没有账号？去注册' : '已有账号？去登录' }}
      </button>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    form: {
      type: Object,
      required: true
    },
    loading: {
      type: Boolean,
      default: false
    },
    mode: {
      type: String,
      required: true
    }
  },
  emits: ['submit', 'switch-mode']
};
</script>
