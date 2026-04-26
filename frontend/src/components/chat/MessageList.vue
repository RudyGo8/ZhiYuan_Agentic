<template>
  <div class="chat-container" ref="chatContainer">
    <div v-if="messages.length === 0" class="welcome-screen">
      <div class="big-avatar">知</div>
      <h3>你好，我是知源助手</h3>
      <p>我可以基于知识库回答问题、梳理资料、辅助分析，并展示检索依据。</p>
    </div>

    <MessageItem
      v-for="(message, index) in messages"
      :key="index"
      :message="message"
    />
  </div>
</template>

<script>
import MessageItem from './MessageItem.vue';

export default {
  components: {
    MessageItem
  },
  props: {
    messages: {
      type: Array,
      default: () => []
    }
  },
  methods: {
    scrollToBottom() {
      if (this.$refs.chatContainer) {
        this.$refs.chatContainer.scrollTop = this.$refs.chatContainer.scrollHeight;
      }
    }
  },
  watch: {
    messages: {
      handler() {
        this.$nextTick(() => this.scrollToBottom());
      },
      deep: true
    }
  }
};
</script>
