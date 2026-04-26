<template>
  <div class="input-area-wrapper">
    <div class="input-area">
      <button class="attach-btn"><i class="fas fa-paperclip"></i></button>
      <textarea
        v-model="localValue"
        @keydown="handleKeyDown"
        @compositionstart="isComposing = true"
        @compositionend="isComposing = false"
        @input="autoResize"
        placeholder="和知源说点什么吧... (Shift+Enter 换行)"
        rows="1"
        ref="textarea"
      ></textarea>
      <button v-if="loading" @click="$emit('stop')" class="send-btn stop-btn" title="终止回答">
        <i class="fas fa-stop"></i>
      </button>
      <button v-else @click="emitSend" class="send-btn" title="发送">
        <i class="fas fa-paper-plane"></i>
      </button>
    </div>
    <div class="footer-text">知源助手会尽量基于知识库生成回答，生成内容仍可能存在偏差，请仔细甄别。</div>
  </div>
</template>

<script>
export default {
  props: {
    loading: {
      type: Boolean,
      default: false
    },
    modelValue: {
      type: String,
      default: ''
    }
  },
  emits: ['update:modelValue', 'send', 'stop'],
  data() {
    return {
      isComposing: false
    };
  },
  computed: {
    localValue: {
      get() {
        return this.modelValue;
      },
      set(value) {
        this.$emit('update:modelValue', value);
      }
    }
  },
  methods: {
    autoResize(event) {
      const textarea = event.target;
      textarea.style.height = 'auto';
      textarea.style.height = `${textarea.scrollHeight}px`;
    },
    resetHeight() {
      if (this.$refs.textarea) {
        this.$refs.textarea.style.height = 'auto';
      }
    },
    emitSend() {
      if (this.isComposing) return;
      this.$emit('send');
      this.$nextTick(() => this.resetHeight());
    },
    handleKeyDown(event) {
      if (event.key === 'Enter' && !event.shiftKey && !this.isComposing) {
        event.preventDefault();
        this.emitSend();
      }
    }
  }
};
</script>
