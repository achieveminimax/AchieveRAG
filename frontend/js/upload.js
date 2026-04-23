/**
 * RAG 知识库助手 - 文档上传模块
 * 
 * 处理文档上传页面的所有交互逻辑
 */

/**
 * 文档上传模块
 */
const UploadModule = {
    // 支持的文件类型
    allowedTypes: ['.pdf', '.txt', '.md', '.docx', '.markdown'],
    
    // 最大文件大小 (50MB)
    maxFileSize: 50 * 1024 * 1024,
    
    // 当前选中的文件
    selectedFiles: [],

    uploadInProgress: false,
    refreshInFlight: false,
    refreshPending: false,
    
    /**
     * 页面进入回调
     */
    onEnter() {
        console.log('Upload page entered');
        this.renderUploadPage();
        this.loadDocumentList();
        this.loadStats();
        this.bindEvents();
    },
    
    /**
     * 渲染上传页面内容
     */
    renderUploadPage() {
        const pageSection = document.getElementById('page-upload');
        if (!pageSection) return;
        
        pageSection.innerHTML = `
            <div class="upload-page">
                <!-- 页面标题 -->
                <div class="page-header">
                    <h1 class="page-title">知识库管理</h1>
                    <p class="page-description">上传和管理您的知识库文档</p>
                </div>
                
                <!-- 上传区域 -->
                <div class="upload-section">
                    <div class="upload-dropzone" id="upload-dropzone">
                        <div class="upload-dropzone-icon">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z" />
                            </svg>
                        </div>
                        <h3 class="upload-dropzone-title">拖拽文件到此处上传</h3>
                        <p class="upload-dropzone-text">或点击选择文件</p>
                        <input type="file" id="file-input" class="file-input" multiple accept=".pdf,.txt,.md,.docx,.markdown">
                        <button class="upload-btn" id="select-file-btn">选择文件</button>
                        <p class="upload-hint">
                            支持格式：PDF、TXT、Markdown、DOCX<br>
                            单个文件最大 50MB
                        </p>
                    </div>
                    
                    <!-- 选中文件列表 -->
                    <div class="selected-files hidden" id="selected-files">
                        <div class="selected-files-header">
                            <h4 class="selected-files-title">待上传文件</h4>
                            <div class="selected-files-progress" id="selected-files-progress"></div>
                        </div>
                        <div class="selected-files-list" id="selected-files-list"></div>
                        <div class="selected-files-actions">
                            <button class="btn btn-secondary" id="clear-files-btn">清空</button>
                            <button class="btn btn-primary" id="upload-files-btn">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z" />
                                </svg>
                                开始上传
                            </button>
                        </div>
                    </div>
                </div>
                
                <!-- 统计信息 -->
                <div class="stats-section" id="stats-section">
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-value" id="stat-total-docs">0</div>
                            <div class="stat-label">文档总数</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value" id="stat-total-chunks">0</div>
                            <div class="stat-label">文本分块</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value" id="stat-total-size">0 MB</div>
                            <div class="stat-label">存储占用</div>
                        </div>
                    </div>
                </div>
                
                <!-- 文档列表 -->
                <div class="documents-section">
                    <div class="section-header">
                        <h2 class="section-title">文档列表</h2>
                        <button class="btn btn-icon" id="refresh-docs-btn" title="刷新">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
                            </svg>
                        </button>
                    </div>
                    <div class="documents-list" id="documents-list">
                        <div class="empty-state">
                            <div class="empty-icon">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                                </svg>
                            </div>
                            <p class="empty-text">暂无文档，请上传文件</p>
                        </div>
                    </div>
            </div>
        `;
    },
    
    /**
     * 绑定事件
     */
    bindEvents() {
        const dropzone = document.getElementById('upload-dropzone');
        const fileInput = document.getElementById('file-input');
        const selectBtn = document.getElementById('select-file-btn');
        const clearBtn = document.getElementById('clear-files-btn');
        const uploadBtn = document.getElementById('upload-files-btn');
        const refreshBtn = document.getElementById('refresh-docs-btn');
        
        // 点击选择文件
        selectBtn?.addEventListener('click', () => fileInput?.click());
        dropzone?.addEventListener('click', (e) => {
            if (e.target === dropzone || e.target.closest('.upload-dropzone-icon')) {
                fileInput?.click();
            }
        });
        
        // 文件选择变化
        fileInput?.addEventListener('change', (e) => {
            this.handleFiles(e.target.files);
        });
        
        // 拖拽事件
        dropzone?.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });
        
        dropzone?.addEventListener('dragleave', () => {
            dropzone.classList.remove('dragover');
        });
        
        dropzone?.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            this.handleFiles(e.dataTransfer.files);
        });
        
        // 清空按钮
        clearBtn?.addEventListener('click', () => {
            this.clearSelectedFiles();
        });
        
        // 上传按钮
        uploadBtn?.addEventListener('click', () => {
            this.uploadFiles();
        });
        
        // 刷新按钮
        refreshBtn?.addEventListener('click', () => {
            this.loadDocumentList();
            this.loadStats();
        });
    },
    
    /**
     * 处理文件选择
     */
    handleFiles(files) {
        if (!files || files.length === 0) return;
        
        for (const file of files) {
            // 检查文件类型
            const ext = '.' + file.name.split('.').pop().toLowerCase();
            if (!this.allowedTypes.includes(ext)) {
                Toast.warning(`不支持的文件类型: ${file.name}`);
                continue;
            }
            
            // 检查文件大小
            if (file.size > this.maxFileSize) {
                Toast.warning(`文件过大: ${file.name} (最大 50MB)`);
                continue;
            }
            
            // 检查是否已存在
            if (this.selectedFiles.some(item => item.file?.name === file.name && item.file?.size === file.size)) {
                continue;
            }
            
            this.selectedFiles.push({
                id: `${file.name}__${file.size}__${file.lastModified}`,
                file,
                status: 'pending',
                error: null,
            });
        }
        
        this.renderSelectedFiles();
    },
    
    /**
     * 渲染选中文件列表
     */
    renderSelectedFiles() {
        const container = document.getElementById('selected-files');
        const list = document.getElementById('selected-files-list');
        const progress = document.getElementById('selected-files-progress');
        
        if (this.selectedFiles.length === 0) {
            container?.classList.add('hidden');
            return;
        }
        
        container?.classList.remove('hidden');

        const total = this.selectedFiles.length;
        const completed = this.selectedFiles.filter(item => item.status === 'success' || item.status === 'error').length;
        const success = this.selectedFiles.filter(item => item.status === 'success').length;
        const percent = total === 0 ? 0 : Math.round((completed / total) * 100);

        if (progress) {
            progress.innerHTML = `
                <div class="upload-progress-text">已完成 ${completed}/${total}（成功 ${success}）</div>
                <div class="upload-progress-bar" aria-hidden="true">
                    <div class="upload-progress-bar-fill" style="width: ${percent}%"></div>
                </div>
            `;
        }

        list.innerHTML = this.selectedFiles.map((item) => `
            <div class="selected-file-item ${item.status ? `file-status-${item.status}` : ''}">
                <div class="file-icon">
                    ${this.getFileIcon(item.file.name)}
                </div>
                <div class="file-info">
                    <div class="file-name">${item.file.name}</div>
                    <div class="file-size">${this.formatFileSize(item.file.size)}</div>
                </div>
                <div class="file-status" title="${item.error ? item.error : ''}">
                    ${this.getFileStatusBadge(item)}
                </div>
                <button class="file-remove" data-id="${item.id}" title="移除" ${this.uploadInProgress ? 'disabled' : ''}>
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>
        `).join('');
        
        // 绑定移除事件
        list.querySelectorAll('.file-remove').forEach(btn => {
            btn.addEventListener('click', (e) => {
                if (this.uploadInProgress) return;
                const id = e.currentTarget.dataset.id;
                const index = this.selectedFiles.findIndex(item => item.id === id);
                if (index >= 0) this.selectedFiles.splice(index, 1);
                this.renderSelectedFiles();
            });
        });
    },

    getFileStatusBadge(item) {
        switch (item.status) {
            case 'uploading':
                return `
                    <span class="file-status-badge badge-uploading">
                        <svg class="spinner" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
                        </svg>
                        上传中
                    </span>
                `;
            case 'success':
                return `
                    <span class="file-status-badge badge-success">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                        </svg>
                        已上传
                    </span>
                `;
            case 'error':
                return `
                    <span class="file-status-badge badge-error">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                        失败
                    </span>
                `;
            default:
                return `<span class="file-status-badge badge-pending">待上传</span>`;
        }
    },
    
    /**
     * 获取文件图标
     */
    getFileIcon(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        const icons = {
            pdf: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" /></svg>`,
            txt: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" /></svg>`,
            md: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" /></svg>`,
            docx: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" /></svg>`,
        };
        return icons[ext] || icons.txt;
    },
    
    /**
     * 格式化文件大小
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const units = ['B', 'KB', 'MB', 'GB'];
        let size = bytes;
        let unitIndex = 0;
        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }
        return `${size.toFixed(1)} ${units[unitIndex]}`;
    },
    
    /**
     * 清空选中文件
     */
    clearSelectedFiles() {
        this.selectedFiles = [];
        this.uploadInProgress = false;
        this.renderSelectedFiles();
        const fileInput = document.getElementById('file-input');
        if (fileInput) fileInput.value = '';
    },

    async refreshDocumentsAndStats() {
        if (this.refreshInFlight) {
            this.refreshPending = true;
            return;
        }
        this.refreshInFlight = true;
        try {
            await Promise.all([
                this.loadDocumentList(),
                this.loadStats(),
            ]);
        } finally {
            this.refreshInFlight = false;
            if (this.refreshPending) {
                this.refreshPending = false;
                this.refreshDocumentsAndStats();
            }
        }
    },
    
    /**
     * 上传文件
     */
    async uploadFiles() {
        if (this.selectedFiles.length === 0) {
            Toast.warning('请先选择文件');
            return;
        }
        
        const uploadBtn = document.getElementById('upload-files-btn');
        const clearBtn = document.getElementById('clear-files-btn');
        this.uploadInProgress = true;
        uploadBtn.disabled = true;
        if (clearBtn) clearBtn.disabled = true;
        uploadBtn.innerHTML = `
            <svg class="spinner" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
            </svg>
            上传中...
        `;
        
        try {
            let successCount = 0;
            let failedCount = 0;
            const failedDetails = [];

            for (const item of this.selectedFiles) {
                if (item.status === 'success') continue;

                item.status = 'uploading';
                item.error = null;
                this.renderSelectedFiles();

                try {
                    const result = await api.uploadDocuments([item.file], { showToast: false });
                    const failed = result?.data?.failed?.[0];

                    if (result?.code === 200 && !failed) {
                        item.status = 'success';
                        successCount++;
                        this.renderSelectedFiles();
                        this.refreshDocumentsAndStats();
                        continue;
                    }

                    item.status = 'error';
                    item.error = failed?.error || result?.message || '上传失败';
                    failedCount++;
                    failedDetails.push(`${item.file.name}: ${item.error}`);
                } catch (error) {
                    item.status = 'error';
                    item.error = error?.message || '上传失败';
                    failedCount++;
                    failedDetails.push(`${item.file.name}: ${item.error}`);
                }

                this.renderSelectedFiles();
            }

            if (successCount > 0) {
                Toast.success(`成功上传 ${successCount} 个文件`);
            }

            if (failedCount > 0) {
                Toast.error(`${failedCount} 个文件上传失败:\n${failedDetails.join('\n')}`);
            }

            const remaining = this.selectedFiles.filter(item => item.status !== 'success');
            if (remaining.length === 0) {
                this.clearSelectedFiles();
            } else {
                this.selectedFiles = remaining.map(item => ({ ...item, status: item.status === 'error' ? 'error' : 'pending' }));
                this.uploadInProgress = false;
                this.renderSelectedFiles();
            }
        } catch (error) {
            console.error('Upload error:', error);
            Toast.error(error.message || '上传失败，请重试');
        } finally {
            this.uploadInProgress = false;
            uploadBtn.disabled = false;
            if (clearBtn) clearBtn.disabled = false;
            uploadBtn.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z" />
                </svg>
                开始上传
            `;
            this.renderSelectedFiles();
        }
    },
    
    /**
     * 加载文档列表
     */
    async loadDocumentList() {
        const list = document.getElementById('documents-list');
        if (!list) return;
        
        list.innerHTML = `
            <div class="loading-state">
                <div class="spinner"></div>
                <p>加载中...</p>
            </div>
        `;
        
        try {
            const result = await api.getDocuments();
            
            if (result.code === 200 && result.data?.documents?.length > 0) {
                if (typeof AppState !== 'undefined') {
                    AppState.set('documents', result.data);
                }
                this.renderDocumentList(result.data.documents);
            } else {
                if (typeof AppState !== 'undefined') {
                    AppState.set('documents', result.data || { documents: [], total: 0 });
                }
                list.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                            </svg>
                        </div>
                        <p class="empty-text">暂无文档，请上传文件</p>
                    </div>
                `;
            }
        } catch (error) {
            if (typeof AppState !== 'undefined') {
                AppState.set('documents', { documents: [], total: 0 });
            }
            console.error('Load documents error:', error);
            list.innerHTML = `
                    <div class="empty-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                        </svg>
                    </div>
                    <p class="empty-text">加载失败，请重试</p>
                </div>
            `;
        }
    },
    
    /**
     * 渲染文档列表
     */
    renderDocumentList(documents) {
        const list = document.getElementById('documents-list');
        if (!list) return;
        
        list.innerHTML = documents.map(doc => `
            <div class="document-item" data-id="${doc.id}">
                <div class="document-icon">
                    ${this.getFileIcon(doc.filename)}
                </div>
                <div class="document-info">
                    <div class="document-name">${doc.filename}</div>
                    <div class="document-meta">
                        <span class="document-size">${this.formatFileSize(doc.file_size)}</span>
                        <span class="document-type">${doc.file_type.toUpperCase()}</span>
                        ${doc.chunk_count ? `<span class="document-chunks">${doc.chunk_count} 个分块</span>` : ''}
                        <span class="document-status status-${doc.status}">${this.getStatusText(doc.status)}</span>
                    </div>
                    <div class="document-time">${this.formatTime(doc.created_at)}</div>
                </div>
                <div class="document-actions">
                    <button class="btn btn-icon btn-preview view-doc-btn" data-id="${doc.id}" data-name="${doc.filename}" title="查看内容">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 12s3.75-7.5 9.75-7.5 9.75 7.5 9.75 7.5-3.75 7.5-9.75 7.5S2.25 12 2.25 12z" />
                            <path stroke-linecap="round" stroke-linejoin="round" d="M12 15.75a3.75 3.75 0 100-7.5 3.75 3.75 0 000 7.5z" />
                        </svg>
                    </button>
                    <button class="btn btn-icon btn-danger delete-doc-btn" data-id="${doc.id}" title="删除">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                        </svg>
                    </button>
                </div>
            </div>
        `).join('');
        
        list.querySelectorAll('.view-doc-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const { id, name } = e.currentTarget.dataset;
                await this.openDocumentPreview(id, name);
            });
        });

        // 绑定删除事件
        list.querySelectorAll('.delete-doc-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const docId = e.currentTarget.dataset.id;
                const docName = e.currentTarget.closest('.document-item').querySelector('.document-name').textContent;
                
                const confirmed = await this.confirmDeleteDocument(docName);
                if (confirmed) {
                    await this.deleteDocument(docId, docName);
                }
            });
        });
    },
    
    /**
     * 获取状态文本
     */
    getStatusText(status) {
        const statusMap = {
            pending: '待处理',
            processing: '处理中',
            completed: '已完成',
            error: '错误',
        };
        return statusMap[status] || status;
    },

    /**
     * 打开文档预览
     * @param {string} docId - 文档 ID
     * @param {string} docName - 文档名称
     */
    async openDocumentPreview(docId, docName = '') {
        try {
            await DocumentPreview.open(docId, { docName });
        } catch (error) {
            console.error('Open document preview error:', error);
        }
    },

    /**
     * 确认删除文档
     * 自定义确认弹窗不可用时，回退到浏览器原生确认框。
     * @param {string} docName - 文档名称
     * @returns {Promise<boolean>}
     */
    async confirmDeleteDocument(docName) {
        if (typeof ConfirmDialog !== 'undefined' && typeof ConfirmDialog.delete === 'function') {
            return ConfirmDialog.delete(docName);
        }

        return window.confirm(`您确定要删除"${docName}"吗？此操作不可撤销。`);
    },
    
    /**
     * 格式化时间
     */
    formatTime(isoString) {
        if (!isoString) return '';
        const date = new Date(isoString);
        return date.toLocaleString('zh-CN');
    },

    /**
     * 删除文档
     * @param {string} docId - 文档 ID
     * @param {string} docName - 文档名称（用于提示）
     */
    async deleteDocument(docId, docName = '') {
        try {
            await api.deleteDocument(docId);
            // 删除成功后刷新列表和统计
            await Promise.all([
                this.loadDocumentList(),
                this.loadStats(),
            ]);
        } catch (error) {
            console.error('Delete error:', error);
            Toast.error(`删除文档 "${docName}" 失败: ${error.message || '未知错误'}`);
        }
    },
    
    /**
     * 加载统计信息
     */
    async loadStats() {
        try {
            const result = await api.getStats();
            if (result.code === 200 && result.data) {
                document.getElementById('stat-total-docs').textContent = result.data.total_documents || 0;
                document.getElementById('stat-total-chunks').textContent = result.data.total_chunks || 0;
                document.getElementById('stat-total-size').textContent = result.data.total_size_human || '0 MB';
            }
        } catch (error) {
            console.error('Load stats error:', error);
        }
    },
};

// 导出（如果支持模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { UploadModule };
}
