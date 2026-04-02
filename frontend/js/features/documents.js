(function bootstrapDocumentFeature(global) {
    global.AppModules = global.AppModules || {};

    function createDocumentMethods() {
        return {
            handleSettings() {
                if (!this.isAdmin) {
                    alert('仅管理员可访问文档管理');
                    return;
                }
                this.activeNav = 'settings';
                this.showHistorySidebar = false;
                this.loadDocuments();
            },

            async loadDocuments() {
                this.documentsLoading = true;
                try {
                    const response = await this.authFetch('/documents');
                    if (!response.ok) {
                        const data = await response.json().catch(() => ({}));
                        throw new Error(data.detail || 'Failed to load documents');
                    }
                    const data = await response.json();
                    this.documents = data.documents;
                } catch (error) {
                    alert(`加载文档列表失败：${error.message}`);
                } finally {
                    this.documentsLoading = false;
                }
            },

            handleFileSelect(event) {
                const files = event.target.files;
                if (files && files.length > 0) {
                    this.selectedFile = files[0];
                    this.uploadProgress = '';
                }
            },

            async uploadDocument() {
                if (!this.selectedFile) {
                    alert('请先选择文件');
                    return;
                }

                this.isUploading = true;
                this.uploadProgress = '正在上传...';
                try {
                    const formData = new FormData();
                    formData.append('file', this.selectedFile);

                    const response = await this.authFetch('/documents/upload', {
                        method: 'POST',
                        body: formData
                    });

                    if (!response.ok) {
                        const error = await response.json().catch(() => ({}));
                        throw new Error(error.detail || 'Upload failed');
                    }

                    const data = await response.json();
                    this.uploadProgress = data.message;
                    this.selectedFile = null;

                    if (this.$refs.fileInput) {
                        this.$refs.fileInput.value = '';
                    }

                    await this.loadDocuments();
                    setTimeout(() => {
                        this.uploadProgress = '';
                    }, 3000);
                } catch (error) {
                    this.uploadProgress = `上传失败：${error.message}`;
                } finally {
                    this.isUploading = false;
                }
            },

            async deleteDocument(filename) {
                if (!confirm(`确定要删除文档 "${filename}" 吗？这将同时删除 Milvus 中的所有相关向量。`)) {
                    return;
                }

                try {
                    const response = await this.authFetch(`/documents/${encodeURIComponent(filename)}`, {
                        method: 'DELETE'
                    });

                    if (!response.ok) {
                        const error = await response.json().catch(() => ({}));
                        throw new Error(error.detail || 'Delete failed');
                    }

                    const data = await response.json();
                    alert(data.message);
                    await this.loadDocuments();
                } catch (error) {
                    alert(`删除文档失败：${error.message}`);
                }
            }
        };
    }

    global.AppModules.createDocumentMethods = createDocumentMethods;
})(window);
