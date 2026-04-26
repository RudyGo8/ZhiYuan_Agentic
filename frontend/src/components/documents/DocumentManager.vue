<template>
  <div class="settings-panel">
    <div class="settings-header">
      <h2><i class="fas fa-cog"></i> 文档管理</h2>
      <p>上传文档进行向量化处理，支持 PDF、Word 和 Excel 格式。</p>
    </div>

    <div class="upload-section">
      <h3><i class="fas fa-upload"></i> 上传文档</h3>
      <div class="upload-area">
        <input
          type="file"
          ref="fileInput"
          @change="handleFileSelect"
          accept=".pdf,.doc,.docx,.xls,.xlsx"
          style="display: none"
        />
        <button @click="$refs.fileInput.click()" class="upload-btn">
          <i class="fas fa-cloud-upload-alt"></i> 选择文件
        </button>
        <div v-if="selectedFile" class="selected-file">
          <i class="fas fa-file"></i> {{ selectedFile.name }}
          <button @click="$emit('upload')" class="btn-primary" :disabled="uploading">
            <i class="fas fa-upload"></i> {{ uploading ? '上传中...' : '开始上传' }}
          </button>
        </div>
        <div v-if="uploadProgress" class="upload-progress">
          {{ uploadProgress }}
        </div>
      </div>
    </div>

    <div class="documents-section">
      <h3><i class="fas fa-list"></i> 已上传文档</h3>
      <button @click="$emit('refresh')" class="btn-secondary">
        <i class="fas fa-sync"></i> 刷新列表
      </button>

      <div v-if="loading" class="loading-indicator">
        加载中...
      </div>

      <div v-else-if="documents.length === 0" class="empty-documents">
        <i class="fas fa-inbox"></i>
        <p>暂无文档</p>
      </div>

      <div v-else class="documents-list">
        <div v-for="doc in documents" :key="doc.filename" class="document-item">
          <div class="document-info">
            <div class="document-icon">
              <i :class="getFileIcon(doc.file_type)"></i>
            </div>
            <div class="document-details">
              <div class="document-name">{{ doc.filename }}</div>
              <div class="document-meta">
                <span>{{ doc.file_type }}</span>
                <span>{{ doc.chunk_count }} 个文本片段</span>
              </div>
            </div>
          </div>
          <button @click="$emit('delete-document', doc.filename)" class="btn-danger" title="删除文档">
            <i class="fas fa-trash"></i>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    documents: {
      type: Array,
      default: () => []
    },
    loading: {
      type: Boolean,
      default: false
    },
    selectedFile: {
      type: Object,
      default: null
    },
    uploading: {
      type: Boolean,
      default: false
    },
    uploadProgress: {
      type: String,
      default: ''
    }
  },
  emits: ['select-file', 'upload', 'refresh', 'delete-document'],
  methods: {
    handleFileSelect(event) {
      const files = event.target.files;
      this.$emit('select-file', files && files.length > 0 ? files[0] : null);
    },
    getFileIcon(fileType) {
      if (fileType === 'PDF') return 'fas fa-file-pdf';
      if (fileType === 'Word') return 'fas fa-file-word';
      if (fileType === 'Excel') return 'fas fa-file-excel';
      return 'fas fa-file';
    }
  }
};
</script>
