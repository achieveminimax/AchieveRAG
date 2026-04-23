/**
 * RAG 知识库助手 - 对话功能模块
 * 
 * 处理对话页面的所有交互逻辑：
 * - 消息渲染（用户/AI 消息气泡）
 * - SSE 流式接收与渲染
 * - 输入框交互
 * - 对话管理
 */

/**
 * 对话模块
 */
const ChatModule = {
    // DOM 元素引用
    elements: {},
    
    // 当前状态
    state: {
        messages: [],
        currentStream: null,
        isGenerating: false,
        selectedDocumentIds: [],
        filterPanelOpen: false
    },

    /**
     * 初始化对话模块
     */
    init() {
        this._cacheElements();
        this._bindEvents();
        this._renderWelcome();
        this._ensureDocumentsLoaded();
    },

    /**
     * 缓存 DOM 元素引用
     * @private
     */
    _cacheElements() {
        this.elements = {
            // 容器
            messagesContainer: document.getElementById('chat-messages-container'),
            messages: document.getElementById('chat-messages'),
            welcome: document.getElementById('chat-welcome'),
            
            // 输入区
            input: document.getElementById('chat-input'),
            sendBtn: document.getElementById('send-btn'),
            clearBtn: document.getElementById('clear-chat-btn'),
            docToggleBtn: document.getElementById('toggle-doc-filter-btn'),
            docToggleLabel: document.getElementById('toggle-doc-filter-label'),
            docFilterPanel: document.getElementById('chat-doc-filter-panel'),
            
            // 建议问题
            suggestions: document.querySelectorAll('.chat-welcome-suggestion')
        };
    },

    /**
     * 绑定事件
     * @private
     */
    _bindEvents() {
        const { input, sendBtn, clearBtn, suggestions, docToggleBtn } = this.elements;

        // 发送按钮点击
        sendBtn?.addEventListener('click', () => this._sendMessage());

        // 输入框键盘事件
        input?.addEventListener('keydown', (e) => this._handleInputKeydown(e));

        // 输入框自动调整高度
        input?.addEventListener('input', () => this._adjustTextareaHeight());

        // 清空按钮
        clearBtn?.addEventListener('click', () => this._clearChat());

        docToggleBtn?.addEventListener('click', () => {
            this.state.filterPanelOpen = !this.state.filterPanelOpen;
            this._updateDocumentSelector();
        });

        // 建议问题点击
        suggestions?.forEach(suggestion => {
            suggestion.addEventListener('click', () => {
                const question = suggestion.dataset.question;
                if (question) {
                    input.value = question;
                    this._adjustTextareaHeight();
                    this._sendMessage();
                }
            });
        });

        document.addEventListener('change', (e) => {
            if (e.target.matches('.chat-doc-option input[type="checkbox"]')) {
                this._syncSelectedDocumentsFromUI();
            }
        });

        document.addEventListener('click', (e) => {
            if (e.target.id === 'clear-doc-filter-btn') {
                this.clearSelectedDocuments();
                return;
            }

            const panel = this.elements.docFilterPanel;
            const toggleBtn = this.elements.docToggleBtn;
            if (
                this.state.filterPanelOpen &&
                panel &&
                toggleBtn &&
                !panel.contains(e.target) &&
                !toggleBtn.contains(e.target)
            ) {
                this.state.filterPanelOpen = false;
                this._updateDocumentSelector();
            }
        });

        this._updateDocumentSelector();
    },

    /**
     * 处理输入框键盘事件
     * @private
     */
    _handleInputKeydown(e) {
        // Enter 发送，Shift+Enter 换行
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this._sendMessage();
        }
    },

    /**
     * 调整输入框高度
     * @private
     */
    _adjustTextareaHeight() {
        const { input } = this.elements;
        if (!input) return;

        // 重置高度以获取正确的 scrollHeight
        input.style.height = 'auto';
        
        // 设置新高度（最大 200px）
        const maxHeight = 200;
        const newHeight = Math.min(input.scrollHeight, maxHeight);
        input.style.height = newHeight + 'px';
        
        // 如果内容超出，启用滚动
        input.style.overflowY = input.scrollHeight > maxHeight ? 'auto' : 'hidden';
    },

    /**
     * 发送消息
     * @private
     */
    async _sendMessage() {
        const { input } = this.elements;
        const question = input?.value.trim();

        if (!question || this.state.isGenerating) return;

        // 获取当前对话 ID
        const conversationId = AppState?.get?.('currentConversationId') || null;
        const selectedDocumentIds = [...this.state.selectedDocumentIds];

        // 添加用户消息到界面
        this._addUserMessage(question, selectedDocumentIds);

        // 清空输入框
        input.value = '';
        input.style.height = 'auto';

        // 隐藏欢迎界面，显示消息列表
        this._showMessages();

        // 开始流式生成
        await this._startStream(question, conversationId, selectedDocumentIds);
    },

    /**
     * 开始流式生成
     * @private
     */
    async _startStream(question, conversationId, documentIds = []) {
        this.state.isGenerating = true;
        this._setInputDisabled(true);

        // 创建 AI 消息气泡
        const aiMessageEl = this._createAIMessageElement();
        this.elements.messages.appendChild(aiMessageEl);

        let fullContent = '';
        let sources = null;
        const selectedDocuments = this._getSelectedDocuments().filter(doc => documentIds.includes(doc.id));
        let renderTimer = null;
        let pendingRender = false;

        const flushRender = (force = false) => {
            pendingRender = false;
            if (renderTimer) {
                clearTimeout(renderTimer);
                renderTimer = null;
            }
            this._renderAIMessage(aiMessageEl, fullContent, !force);
            this._scrollToBottom(force);
        };

        const scheduleRender = () => {
            if (pendingRender) return;
            pendingRender = true;
            renderTimer = setTimeout(() => {
                flushRender(false);
            }, 50);
        };

        // 滚动到底部
        this._scrollToBottom(true);

        // 启动 SSE 流
        this.state.currentStream = api.chatStream(question, conversationId, {
            // 收到 token
            onToken: (content) => {
                fullContent += content;
                scheduleRender();
            },

            // 收到来源引用
            onSources: (src) => {
                sources = src;
            },

            // 完成
            onDone: (data) => {
                flushRender(true);
                this._finishStream(aiMessageEl, fullContent, sources, data, selectedDocuments);
            },

            // 错误
            onError: (error) => {
                if (renderTimer) {
                    clearTimeout(renderTimer);
                }
                this._handleStreamError(aiMessageEl, error);
            }
        }, {
            documentIds,
        });
    },

    /**
     * 完成流式生成
     * @private
     */
    _finishStream(messageEl, content, sources, data, selectedDocuments = []) {
        // 移除打字光标
        const cursorEl = messageEl.querySelector('.typing-cursor');
        if (cursorEl) cursorEl.remove();

        this._addAnswerScope(messageEl, selectedDocuments, sources);

        // 添加来源引用
        if (sources && sources.length > 0) {
            this._addSources(messageEl, sources);
        }

        // 添加操作按钮
        this._addMessageActions(messageEl, content);

        // 更新状态
        this.state.isGenerating = false;
        this._setInputDisabled(false);
        this.state.currentStream = null;

        // 更新全局对话 ID
        if (data?.conversation_id) {
            AppState.set('currentConversationId', data.conversation_id);
        }

        // 保存消息到历史
        this.state.messages.push(
            { role: 'user', content: messageEl.previousElementSibling?.querySelector('.message-text')?.textContent || '' },
            { role: 'assistant', content, sources, selected_documents: selectedDocuments }
        );

        api.getConversations()
            .then((resp) => {
                const conversations = resp?.data?.conversations || [];
                AppState.set('conversations', conversations);
            })
            .catch(() => {});
    },

    /**
     * 处理流式错误
     * @private
     */
    _handleStreamError(messageEl, error) {
        const contentEl = messageEl.querySelector('.message-text');
        const cursorEl = messageEl.querySelector('.typing-cursor');
        if (cursorEl) cursorEl.remove();

        // 显示错误信息
        const errorDiv = document.createElement('div');
        errorDiv.className = 'message-error';
        errorDiv.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>
            <span>生成失败: ${error.message || '请稍后重试'}</span>
        `;
        contentEl.appendChild(errorDiv);

        this.state.isGenerating = false;
        this._setInputDisabled(false);
        this.state.currentStream = null;
    },

    /**
     * 添加用户消息
     * @private
     */
    _addUserMessage(content, documentIds = []) {
        const selectedDocuments = this._getSelectedDocuments().filter(doc => documentIds.includes(doc.id));
        const selectedDocsHtml = selectedDocuments.length > 0
            ? `
                <div class="message-user-files">
                    ${selectedDocuments.map(doc => `
                        <span class="message-user-file-tag">${this._escapeHtml(doc.filename)}</span>
                    `).join('')}
                </div>
            `
            : '';

        const messageEl = document.createElement('div');
        messageEl.className = 'message message-user';
        messageEl.innerHTML = `
            <div class="message-avatar">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
                </svg>
            </div>
            <div class="message-content">
                <div class="message-bubble">
                    ${selectedDocsHtml}
                    <div class="message-text">${this._escapeHtml(content)}</div>
                </div>
            </div>
        `;

        this.elements.messages.appendChild(messageEl);
        this._scrollToBottom(true);
    },

    /**
     * 创建 AI 消息元素
     * @private
     */
    _createAIMessageElement() {
        const messageEl = document.createElement('div');
        messageEl.className = 'message message-ai';
        messageEl.innerHTML = `
            <div class="message-avatar">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
                </svg>
            </div>
            <div class="message-content">
                <div class="message-bubble">
                    <div class="thought-container collapsed" style="display: none;">
                        <div class="thought-header">
                            <div class="thought-title-wrapper">
                                <svg class="thought-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.82 1.508-2.316a7.5 7.5 0 10-7.516 0c.85.496 1.508 1.333 1.508 2.316V18" />
                                </svg>
                                <span class="thought-title">深度思考</span>
                            </div>
                            <svg class="thought-toggle-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                            </svg>
                        </div>
                        <div class="thought-content">
                            <div class="thought-text"></div>
                        </div>
                    </div>
                    <div class="message-text"></div>
                    <span class="typing-cursor"></span>
                </div>
            </div>
        `;
        
        // 绑定展开/折叠事件
        const thoughtHeader = messageEl.querySelector('.thought-header');
        const thoughtContainer = messageEl.querySelector('.thought-container');
        if (thoughtHeader && thoughtContainer) {
            thoughtHeader.addEventListener('click', () => {
                thoughtContainer.classList.toggle('expanded');
                thoughtContainer.classList.toggle('collapsed');
            });
        }

        return messageEl;
    },

    /**
     * 渲染 AI 消息内容（处理思考过程与正文）
     * @private
     */
    _renderAIMessage(aiMessageEl, content, isStreaming = false) {
        const thoughtContainer = aiMessageEl.querySelector('.thought-container');
        const thoughtText = aiMessageEl.querySelector('.thought-text');
        const messageText = aiMessageEl.querySelector('.message-text');

        if (!thoughtContainer || !thoughtText || !messageText) {
            const target = aiMessageEl.querySelector('.message-text') || aiMessageEl;
            this._renderMarkdown(target, content, { enableCopyButtons: !isStreaming });
            return;
        }

        let thoughtStr = '';
        let mainStr = content;

        // 匹配 <think>...</think> 或未闭合的 <think>...
        const thinkMatch = content.match(/<think>([\s\S]*?)(?:<\/think>|$)/);
        
        if (thinkMatch) {
            thoughtStr = thinkMatch[1].trim();
            mainStr = content.replace(/<think>[\s\S]*?(?:<\/think>|$)/, '').trim();
            
            thoughtContainer.style.display = 'block';
            thoughtText.textContent = thoughtStr;
            
            // 判断是否在思考中 (未出现闭合标签)
            if (!content.includes('</think>')) {
                thoughtContainer.classList.add('thinking');
                // 流式思考中，自动展开
                if (isStreaming) {
                    thoughtContainer.classList.add('expanded');
                    thoughtContainer.classList.remove('collapsed');
                }
            } else {
                thoughtContainer.classList.remove('thinking');
            }
        } else {
            thoughtContainer.style.display = 'none';
        }

        // 解析并渲染剩下的正文
        this._renderMarkdown(messageText, mainStr, { enableCopyButtons: !isStreaming });
    },

    /**
     * 渲染 Markdown 内容
     * @private
     */
    _renderMarkdown(element, content, options = {}) {
        const { enableCopyButtons = true } = options;
        // 使用 marked 解析 Markdown
        if (typeof marked !== 'undefined') {
            try {
                element.innerHTML = marked.parse(content, {
                    breaks: true,
                    gfm: true
                });
                
                // 为代码块添加复制按钮
                if (enableCopyButtons) {
                    this._addCodeCopyButtons(element);
                }
            } catch (e) {
                console.warn('[Chat] marked.parse 失败，使用纯文本:', e);
                // CSP 或解析错误时降级为纯文本
                element.textContent = content;
            }
        } else {
            element.textContent = content;
        }
    },

    /**
     * 为代码块添加复制按钮
     * @private
     */
    _addCodeCopyButtons(container) {
        const codeBlocks = container.querySelectorAll('pre code');
        
        codeBlocks.forEach(codeBlock => {
            const pre = codeBlock.parentElement;
            
            // 检查是否已添加复制按钮
            if (pre.querySelector('.code-copy-btn')) return;
            
            const copyBtn = document.createElement('button');
            copyBtn.className = 'code-copy-btn';
            copyBtn.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 011.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 00-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 01-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 00-3.375-3.375h-1.5" />
                </svg>
                <span>复制</span>
            `;
            
            copyBtn.addEventListener('click', async () => {
                const code = codeBlock.textContent;
                const success = await copyToClipboard(code);
                if (success) {
                    copyBtn.innerHTML = `
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                        </svg>
                        <span>已复制</span>
                    `;
                    setTimeout(() => {
                        copyBtn.innerHTML = `
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 011.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 00-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 01-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 00-3.375-3.375h-1.5" />
                            </svg>
                            <span>复制</span>
                        `;
                    }, 2000);
                }
            });
            
            pre.style.position = 'relative';
            pre.appendChild(copyBtn);
        });
    },

    /**
     * 添加来源引用
     * @private
     */
    _addSources(messageEl, sources) {
        const contentEl = messageEl.querySelector('.message-content');
        
        const sourcesEl = document.createElement('div');
        sourcesEl.className = 'message-sources';
        const groupedSources = this._groupSourcesByDocument(sources);

        const sourcesHtml = groupedSources.map((group, groupIndex) => {
            const itemsHtml = group.items.map(item => `
                <button
                    type="button"
                    class="message-source-item"
                    data-document-id="${this._escapeHtml(item.documentId || '')}"
                    data-source-name="${this._escapeHtml(group.source)}"
                    data-page="${item.page ?? ''}"
                    data-text="${this._escapeHtml(item.text || '')}"
                    title="打开文档预览"
                >
                    <span class="message-source-index">[${item.index}]</span>
                    ${item.page ? `<span class="message-source-page">第 ${item.page} 页</span>` : '<span class="message-source-page">片段内容</span>'}
                    <span class="message-source-score">${item.scoreText}</span>
                </button>
            `).join('');

            return `
                <details class="message-source-group" ${groupIndex === 0 ? 'open' : ''}>
                    <summary class="message-source-group-summary">
                        <div class="message-source-group-main">
                            <span class="message-source-name">${this._escapeHtml(group.source)}</span>
                            <span class="message-source-count">${group.items.length} 条引用</span>
                        </div>
                        <div class="message-source-group-meta">
                            <span class="message-source-score">${group.bestScoreText}</span>
                            <span class="message-source-group-arrow">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                                </svg>
                            </span>
                        </div>
                    </summary>
                    <div class="message-source-group-list">${itemsHtml}</div>
                </details>
            `;
        }).join('');
        
        sourcesEl.innerHTML = `
            <div class="message-sources-title">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
                </svg>
                <span>参考来源</span>
            </div>
            <div class="message-sources-list">${sourcesHtml}</div>
        `;
        
        contentEl.appendChild(sourcesEl);

        sourcesEl.querySelectorAll('.message-source-item[data-document-id]').forEach(item => {
            item.addEventListener('click', async (e) => {
                const button = e.currentTarget;
                const docId = button.dataset.documentId || this._findDocumentIdBySourceName(button.dataset.sourceName || '');
                if (!docId) {
                    Toast.warning('当前来源缺少文档 ID，无法打开预览');
                    return;
                }

                try {
                    await DocumentPreview.open(docId, {
                        docName: button.dataset.sourceName || '',
                        page: button.dataset.page ? Number(button.dataset.page) : null,
                        text: button.dataset.text || '',
                    });
                } catch (error) {
                    console.error('Open source preview error:', error);
                }
            });
        });
    },

    /**
     * 按文档分组来源引用
     * @private
     */
    _groupSourcesByDocument(sources) {
        const groups = new Map();

        sources.forEach((source, index) => {
            const sourceName = source?.source || '未知文档';
            const normalizedScore = Number(source?.score || 0);

            if (!groups.has(sourceName)) {
                groups.set(sourceName, {
                    source: sourceName,
                    bestScore: normalizedScore,
                    items: []
                });
            }

            const group = groups.get(sourceName);
            group.bestScore = Math.max(group.bestScore, normalizedScore);
            group.items.push({
                index: index + 1,
                page: source?.page,
                score: normalizedScore,
                scoreText: `${(normalizedScore * 100).toFixed(0)}%`,
                documentId: source?.document_id || '',
                text: source?.text || '',
            });
        });

        return Array.from(groups.values())
            .map(group => this._deduplicateGroupItemsByPage(group))
            .sort((a, b) => b.bestScore - a.bestScore);
    },

    /**
     * 同一文档下按页码去重；无页码的来源保持原样
     * @private
     */
    _deduplicateGroupItemsByPage(group) {
        const pageMap = new Map();
        const noPageItems = [];

        group.items.forEach(item => {
            if (item.page == null || item.page === '') {
                noPageItems.push(item);
                return;
            }

            const pageKey = String(item.page);
            const existing = pageMap.get(pageKey);
            if (!existing || item.score > existing.score) {
                pageMap.set(pageKey, item);
            }
        });

        const deduplicatedItems = [
            ...Array.from(pageMap.values()).sort((a, b) => (Number(a.page) || 0) - (Number(b.page) || 0)),
            ...noPageItems,
        ];

        const bestScore = deduplicatedItems.reduce(
            (maxScore, item) => Math.max(maxScore, item.score || 0),
            group.bestScore || 0,
        );

        return {
            ...group,
            items: deduplicatedItems,
            bestScore,
            bestScoreText: `${(bestScore * 100).toFixed(0)}%`,
        };
    },

    /**
     * 添加消息操作按钮
     * @private
     */
    _addMessageActions(messageEl, content) {
        const contentEl = messageEl.querySelector('.message-content');
        
        const actionsEl = document.createElement('div');
        actionsEl.className = 'message-actions';
        actionsEl.innerHTML = `
            <button class="message-action-btn" title="复制内容">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 011.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 00-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 01-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 00-3.375-3.375h-1.5" />
                </svg>
            </button>
        `;
        
        // 复制按钮事件
        const copyBtn = actionsEl.querySelector('.message-action-btn');
        copyBtn.addEventListener('click', () => copyToClipboard(content));
        
        contentEl.appendChild(actionsEl);
    },

    /**
     * 设置输入框禁用状态
     * @private
     */
    _setInputDisabled(disabled) {
        const { input, sendBtn } = this.elements;
        
        if (input) {
            input.disabled = disabled;
            if (disabled) {
                input.placeholder = 'AI 正在思考中...';
            } else {
                input.placeholder = '输入您的问题...';
                input.focus();
            }
        }
        
        if (sendBtn) {
            sendBtn.disabled = disabled;
            sendBtn.classList.toggle('disabled', disabled);
        }

        // 更新全局状态
        if (typeof AppState !== 'undefined') {
            AppState.set('isGenerating', disabled);
        }
    },

    /**
     * 滚动到底部
     * @private
     */
    _scrollToBottom(force = false) {
        const { messagesContainer } = this.elements;
        if (messagesContainer) {
            if (!force) {
                const distanceToBottom = messagesContainer.scrollHeight - (messagesContainer.scrollTop + messagesContainer.clientHeight);
                if (distanceToBottom > 120) return;
            }
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    },

    /**
     * 显示消息列表
     * @private
     */
    _showMessages() {
        const { welcome, messages } = this.elements;
        
        if (welcome) welcome.classList.add('hidden');
        if (messages) messages.classList.remove('hidden');
    },

    /**
     * 渲染文档筛选器
     * @private
     */
    _updateDocumentSelector() {
        const panel = this.elements.docFilterPanel;
        const toggleBtn = this.elements.docToggleBtn;
        const toggleLabel = this.elements.docToggleLabel;
        if (!panel || !toggleBtn || !toggleLabel) return;

        const documents = this._getAvailableDocuments();
        const validDocumentIds = new Set(documents.map(doc => doc.id));
        this.state.selectedDocumentIds = this.state.selectedDocumentIds.filter(id => validDocumentIds.has(id));
        const selectedCount = this.state.selectedDocumentIds.length;
        const selectedNames = this._getSelectedDocuments().map(doc => doc.filename);

        toggleBtn.classList.toggle('active', selectedCount > 0);
        toggleLabel.textContent = selectedCount > 0 ? `已选 ${selectedCount} 个文档` : '选择文档';
        toggleBtn.title = selectedNames.length > 0 ? selectedNames.join('、') : '选择文档';
        panel.classList.toggle('hidden', !this.state.filterPanelOpen);

        panel.innerHTML = `
            <div class="chat-doc-filter-header">
                <div>
                    <div class="chat-doc-filter-title">指定回答文档</div>
                    <div class="chat-doc-filter-subtitle">
                        ${documents.length > 0 ? '可多选；不选择时默认检索全部文档' : '暂无可选文档'}
                    </div>
                </div>
                <button class="chat-doc-filter-clear ${selectedCount === 0 ? 'hidden' : ''}" id="clear-doc-filter-btn" type="button">
                    清空选择
                </button>
            </div>
            <div class="chat-doc-filter-list">
                ${documents.length > 0 ? documents.map(doc => `
                    <label class="chat-doc-option">
                        <input type="checkbox" value="${doc.id}" ${this.state.selectedDocumentIds.includes(doc.id) ? 'checked' : ''}>
                        <span class="chat-doc-option-name">${this._escapeHtml(doc.filename)}</span>
                    </label>
                `).join('') : '<div class="chat-doc-filter-empty">请先上传并处理文档</div>'}
            </div>
        `;
    },

    /**
     * 从界面同步已选文档
     * @private
     */
    _syncSelectedDocumentsFromUI() {
        const checkboxes = document.querySelectorAll('.chat-doc-option input[type="checkbox"]:checked');
        this.state.selectedDocumentIds = Array.from(checkboxes).map(item => item.value);
        this._updateDocumentSelector();
    },

    /**
     * 清空已选文档
     */
    clearSelectedDocuments() {
        this.state.selectedDocumentIds = [];
        this._updateDocumentSelector();
    },

    /**
     * 获取可选文档
     * @private
     */
    _getAvailableDocuments() {
        const docsData = AppState?.get?.('documents');
        const docs = Array.isArray(docsData?.documents) ? docsData.documents : [];
        return docs.filter(doc => doc.status !== 'error');
    },

    /**
     * 获取当前已选文档详情
     * @private
     */
    _getSelectedDocuments() {
        const docs = this._getAvailableDocuments();
        return docs.filter(doc => this.state.selectedDocumentIds.includes(doc.id));
    },

    /**
     * 通过来源文件名查找文档 ID
     * @private
     */
    _findDocumentIdBySourceName(sourceName) {
        if (!sourceName) return '';
        const docs = this._getAvailableDocuments();
        const matched = docs.find(doc => doc.filename === sourceName);
        return matched?.id || '';
    },

    /**
     * 确保已加载文档列表
     * @private
     */
    async _ensureDocumentsLoaded() {
        const docsData = AppState?.get?.('documents');
        const hasDocuments = Array.isArray(docsData?.documents);
        if (hasDocuments) {
            this._updateDocumentSelector();
            return;
        }

        try {
            const result = await api.getDocuments();
            if (result?.data && typeof AppState !== 'undefined') {
                AppState.set('documents', result.data);
            }
        } catch (error) {
            console.error('Load chat documents error:', error);
            this._updateDocumentSelector();
        }
    },

    /**
     * 渲染欢迎界面
     * @private
     */
    _renderWelcome() {
        const { welcome, messages } = this.elements;
        
        if (welcome) welcome.classList.remove('hidden');
        if (messages) {
            messages.innerHTML = '';
            messages.classList.add('hidden');
        }
        
        this.state.messages = [];
        this.clearSelectedDocuments();
        this.state.filterPanelOpen = false;
        this._updateDocumentSelector();
    },

    /**
     * 清空对话
     * @private
     */
    async _clearChat() {
        if (this.state.isGenerating) {
            // 如果正在生成，先停止
            if (this.state.currentStream) {
                this.state.currentStream.abort();
                this.state.currentStream = null;
            }
            this.state.isGenerating = false;
        }

        const confirmed = await ConfirmDialog.show({
            title: '清空对话',
            message: '确定要清空当前对话吗？此操作不可撤销。',
            confirmText: '清空',
            cancelText: '取消',
            type: 'warning'
        });

        if (confirmed) {
            this._renderWelcome();
            
            // 重置对话 ID
            if (typeof AppState !== 'undefined') {
                AppState.set('currentConversationId', null);
            }
            
            Toast.success('对话已清空');
        }
    },

    /**
     * 加载对话历史
     * @param {Array} messages - 消息列表
     */
    loadConversation(messages) {
        this._renderWelcome();
        this._showMessages();
        
        const container = this.elements.messages;
        container.innerHTML = '';
        
        messages.forEach(msg => {
            if (msg.role === 'user') {
                this._addUserMessage(msg.content);
            } else if (msg.role === 'assistant') {
                const aiEl = this._createAIMessageElement();
                container.appendChild(aiEl);
                
                // 移除历史消息中的打字光标
                const cursorEl = aiEl.querySelector('.typing-cursor');
                if (cursorEl) cursorEl.remove();
                
                this._renderAIMessage(aiEl, msg.content, false);
                
                if (msg.selected_documents || msg.sources) {
                    this._addAnswerScope(aiEl, msg.selected_documents || [], msg.sources || []);
                }

                if (msg.sources) {
                    this._addSources(aiEl, msg.sources);
                }
                
                this._addMessageActions(aiEl, msg.content);
            }
        });
        
        this._scrollToBottom(true);
    },

    /**
     * 转义 HTML 特殊字符
     * @private
     */
    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * 在回答中显示本次作答所基于的文件
     * @private
     */
    _addAnswerScope(messageEl, selectedDocuments = [], sources = []) {
        const bubble = messageEl.querySelector('.message-bubble');
        if (!bubble || bubble.querySelector('.message-answer-scope')) return;

        const fileNames = selectedDocuments.length > 0
            ? selectedDocuments.map(doc => doc.filename)
            : [...new Set((sources || []).map(source => source?.source).filter(Boolean))];

        const title = selectedDocuments.length > 0 ? '本次基于以下文档作答' : '本次回答参考了以下文档';
        const scopeEl = document.createElement('div');
        scopeEl.className = 'message-answer-scope';

        if (fileNames.length === 0) {
            scopeEl.innerHTML = `
                <div class="message-answer-scope-title">${title}</div>
                <div class="message-answer-scope-empty">未识别到明确文档</div>
            `;
        } else {
            scopeEl.innerHTML = `
                <div class="message-answer-scope-title">${title}</div>
                <div class="message-answer-scope-tags">
                    ${fileNames.map(name => `<span class="message-answer-scope-tag">${this._escapeHtml(name)}</span>`).join('')}
                </div>
            `;
        }

        const messageText = bubble.querySelector('.message-text');
        if (messageText) {
            bubble.insertBefore(scopeEl, messageText);
        } else {
            bubble.prepend(scopeEl);
        }
    },

    /**
     * 新建对话
     */
    newChat() {
        if (this.state.isGenerating) {
            if (this.state.currentStream) {
                this.state.currentStream.abort();
            }
            this.state.currentStream = null;
            this.state.isGenerating = false;
            this._setInputDisabled(false);
        }
        
        this._renderWelcome();
        
        if (typeof AppState !== 'undefined') {
            AppState.set('currentConversationId', null);
        }
    }
};


// 导出（如果支持模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ChatModule };
}
