/**
 * RAG 知识库助手 - 文档预览共享模块
 *
 * 在不同页面复用统一的文档预览弹窗、格式渲染与定位逻辑。
 */
const DocumentPreview = {
    initialized: false,

    /**
     * 打开文档预览
     * @param {string} docId - 文档 ID
     * @param {Object} options - 预览选项
     * @returns {Promise<void>}
     */
    async open(docId, options = {}) {
        if (!docId) {
            throw new Error('缺少文档 ID，无法打开预览');
        }

        this.ensureModal();

        const {
            docName = '',
            page = null,
            text = '',
        } = options;

        const overlay = document.getElementById('document-preview-overlay');
        const title = document.getElementById('document-preview-title');
        const subtitle = document.getElementById('document-preview-subtitle');
        const body = document.getElementById('document-preview-body');

        if (!overlay || !title || !subtitle || !body) return;

        title.textContent = docName || '文档预览';
        subtitle.textContent = '正在加载文档内容...';
        body.innerHTML = `
            <div class="loading-state document-preview-loading">
                <div class="spinner"></div>
                <p>正在解析文档内容...</p>
            </div>
        `;
        overlay.classList.add('show');
        document.body.classList.add('document-preview-open');

        try {
            const result = await this.fetchDocumentPreview(docId);
            if (result.code !== 200 || !result.data) {
                throw new Error(result.message || '获取文档内容失败');
            }

            const preview = result.data;
            subtitle.textContent = this.buildSubtitle(preview.file_type, page);
            this.render(preview, { page, text });
        } catch (error) {
            console.error('Preview document error:', error);
            subtitle.textContent = '加载失败';
            body.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m0 3.75h.008v.008H12v-.008zm9.303 3.376c.866 1.5-.217 3.374-1.948 3.374H4.645c-1.73 0-2.813-1.874-1.948-3.374L10.051 3.378c.866-1.5 3.032-1.5 3.898 0l7.354 12.748z" />
                        </svg>
                    </div>
                    <p class="empty-text">文档内容加载失败，请重试</p>
                </div>
            `;
            if (typeof Toast !== 'undefined') {
                Toast.error(error.message || '获取文档内容失败');
            }
        }
    },

    /**
     * 确保弹窗已存在
     */
    ensureModal() {
        if (this.initialized && document.getElementById('document-preview-overlay')) {
            return;
        }

        let overlay = document.getElementById('document-preview-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'document-preview-overlay';
            overlay.id = 'document-preview-overlay';
            overlay.innerHTML = `
                <div class="document-preview-modal" role="dialog" aria-modal="true" aria-labelledby="document-preview-title">
                    <div class="document-preview-header">
                        <div>
                            <h3 class="document-preview-title" id="document-preview-title">文档预览</h3>
                            <p class="document-preview-subtitle" id="document-preview-subtitle">查看上传文档的内容</p>
                        </div>
                        <button class="btn btn-icon document-preview-close" id="document-preview-close" title="关闭">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                    <div class="document-preview-body" id="document-preview-body"></div>
                </div>
            `;
            document.body.appendChild(overlay);
        }

        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                this.close();
            }
        });

        const closeBtn = document.getElementById('document-preview-close');
        closeBtn?.addEventListener('click', () => this.close());

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.close();
            }
        });

        this.initialized = true;
    },

    /**
     * 获取文档预览数据
     * @param {string} docId - 文档 ID
     * @returns {Promise<Object>}
     */
    async fetchDocumentPreview(docId) {
        if (api && typeof api.getDocumentContent === 'function') {
            return api.getDocumentContent(docId);
        }

        if (api && typeof api.get === 'function') {
            return api.get(`/documents/${docId}/content`);
        }

        throw new Error('文档预览接口不可用，请刷新页面后重试');
    },

    /**
     * 关闭文档预览
     */
    close() {
        const overlay = document.getElementById('document-preview-overlay');
        overlay?.classList.remove('show');
        document.body.classList.remove('document-preview-open');
    },

    /**
     * 渲染预览内容
     * @param {Object} preview - 预览数据
     * @param {Object} focus - 定位信息
     */
    render(preview, focus = {}) {
        const body = document.getElementById('document-preview-body');
        if (!body) return;

        const normalizedType = String(preview.file_type || '').toLowerCase();
        body.classList.toggle('document-preview-pdf', normalizedType === 'pdf');

        const sections = Array.isArray(preview.sections) ? preview.sections : [];
        if (sections.length === 0) {
            body.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                        </svg>
                    </div>
                    <p class="empty-text">文档暂无可预览内容</p>
                </div>
            `;
            return;
        }

        const focusIndex = this.findFocusSectionIndex(sections, focus);
        body.innerHTML = `
            ${preview.truncated ? '<div class="document-preview-tip">文档较长，当前仅展示部分内容。</div>' : ''}
            ${sections.map((section, index) => `
                <section
                    class="document-preview-section ${normalizedType === 'pdf' ? 'document-preview-page-card' : ''} ${index === focusIndex ? 'is-focused' : ''}"
                    data-index="${index}"
                    data-page="${section.page || ''}"
                    data-section="${section.section ?? ''}"
                    data-paragraph="${section.paragraph ?? ''}"
                    data-heading="${this.escapeAttribute(section.heading || '')}"
                >
                    <h4 class="document-preview-section-title">
                        ${this.escapeHtml(section.label || '内容')}
                        ${normalizedType === 'pdf' && section.page ? `<span class="document-preview-page-badge">第 ${section.page} 页</span>` : ''}
                    </h4>
                    <div class="document-preview-section-content ${this.getPreviewContentClass(preview.file_type)}">
                        ${this.renderSectionContent(section, preview.file_type)}
                    </div>
                </section>
            `).join('')}
        `;

        window.requestAnimationFrame(() => {
            if (focusIndex >= 0) {
                const target = body.querySelector(`.document-preview-section[data-index="${focusIndex}"]`);
                target?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }

            this.applyHighlights(body, focus, focusIndex);
        });
    },

    /**
     * 查找应该聚焦的分段
     * @param {Array} sections - 分段列表
     * @param {Object} focus - 定位信息
     * @returns {number}
     */
    findFocusSectionIndex(sections, focus = {}) {
        const { page, text } = focus;
        if (!Array.isArray(sections) || sections.length === 0) return -1;

        if (page != null) {
            const pageIndex = sections.findIndex(section => Number(section.page) === Number(page));
            if (pageIndex >= 0) return pageIndex;
        }

        const normalizedNeedle = this.normalizeText(text);
        if (normalizedNeedle) {
            const exactIndex = sections.findIndex(section => this.normalizeText(section.content).includes(normalizedNeedle));
            if (exactIndex >= 0) return exactIndex;

            const partialNeedle = normalizedNeedle.slice(0, Math.min(normalizedNeedle.length, 80));
            const partialIndex = sections.findIndex(section => this.normalizeText(section.content).includes(partialNeedle));
            if (partialIndex >= 0) return partialIndex;
        }

        return -1;
    },

    /**
     * 渲染单个分段内容
     * @param {Object} section - 分段数据
     * @param {string} fileType - 文件类型
     * @returns {string}
     */
    renderSectionContent(section, fileType) {
        const content = section?.content || '';
        const normalizedType = String(fileType || '').toLowerCase();

        if (normalizedType === 'markdown' || normalizedType === 'md') {
            if (typeof marked !== 'undefined') {
                try {
                    return marked.parse(content, { breaks: true, gfm: true });
                } catch (error) {
                    console.warn('Markdown preview render failed:', error);
                }
            }
        }

        return `<pre>${this.escapeHtml(content)}</pre>`;
    },

    /**
     * 获取内容容器 class
     * @param {string} fileType - 文件类型
     * @returns {string}
     */
    getPreviewContentClass(fileType) {
        const normalizedType = String(fileType || '').toLowerCase();
        return normalizedType === 'markdown' || normalizedType === 'md'
            ? 'document-preview-section-markdown'
            : 'document-preview-section-plain';
    },

    /**
     * 构建副标题
     * @param {string} fileType - 文件类型
     * @param {?number} page - 页码
     * @returns {string}
     */
    buildSubtitle(fileType, page) {
        const parts = [`文件类型：${String(fileType || '').toUpperCase() || '未知'}`];
        if (page != null) {
            parts.push(`已定位到第 ${page} 页`);
        }
        return parts.join(' · ');
    },

    /**
     * 高亮命中的关键词片段
     * @param {HTMLElement} body
     * @param {Object} focus
     * @param {number} focusIndex
     */
    applyHighlights(body, focus = {}, focusIndex = -1) {
        const terms = this.extractHighlightTerms(focus.text || '');
        if (terms.length === 0) return;

        const targets = [];

        if (focusIndex >= 0) {
            const focused = body.querySelector(`.document-preview-section[data-index="${focusIndex}"] .document-preview-section-content`);
            if (focused) targets.push(focused);
        }

        body.querySelectorAll('.document-preview-section .document-preview-section-content').forEach((node) => {
            if (!targets.includes(node)) targets.push(node);
        });

        let totalHighlighted = 0;
        for (const target of targets) {
            const allowInPre = target.classList.contains('document-preview-section-plain');
            totalHighlighted += this.highlightWithinElement(target, terms, { allowInPre, maxHighlights: 60 - totalHighlighted });
            if (totalHighlighted > 0) break;
        }
    },

    /**
     * 从命中文本中提取高亮关键词
     * @param {string} text
     * @returns {string[]}
     */
    extractHighlightTerms(text) {
        const normalized = this.normalizeText(text);
        if (!normalized) return [];

        const terms = new Set();

        const chineseMatches = normalized.match(/[\u4e00-\u9fa5]{2,}/g) || [];
        chineseMatches.forEach(item => terms.add(item));

        const latinMatches = normalized
            .replace(/[^A-Za-z0-9\s]+/g, ' ')
            .split(/\s+/)
            .map(item => item.trim())
            .filter(item => item.length >= 3);
        latinMatches.forEach(item => terms.add(item));

        const numbers = normalized.match(/\b\d{2,}\b/g) || [];
        numbers.forEach(item => terms.add(item));

        return Array.from(terms)
            .filter(item => item.length <= 32)
            .sort((a, b) => b.length - a.length)
            .slice(0, 10);
    },

    /**
     * 在元素内高亮关键词
     * @param {HTMLElement} container
     * @param {string[]} terms
     */
    highlightWithinElement(container, terms, options = {}) {
        const { allowInPre = false, maxHighlights = 50 } = options;
        const normalizedTerms = terms
            .map(term => ({ raw: term, lower: term.toLowerCase() }))
            .filter(term => term.raw);

        if (normalizedTerms.length === 0) return;

        const nodes = [];
        const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, {
            acceptNode: (node) => {
                const parent = node.parentElement;
                if (!parent) return NodeFilter.FILTER_REJECT;
                if (parent.closest('mark')) return NodeFilter.FILTER_REJECT;
                if (!allowInPre && parent.closest('pre, code')) return NodeFilter.FILTER_REJECT;
                if (!node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
                return NodeFilter.FILTER_ACCEPT;
            }
        });

        while (walker.nextNode()) {
            nodes.push(walker.currentNode);
        }

        let highlightedCount = 0;
        nodes.forEach(node => {
            if (highlightedCount >= maxHighlights) return;
            const original = node.nodeValue;
            const originalLower = original.toLowerCase();

            let startIndex = 0;
            let replaced = false;
            const fragment = document.createDocumentFragment();

            while (startIndex < original.length) {
                if (highlightedCount >= maxHighlights) {
                    fragment.appendChild(document.createTextNode(original.slice(startIndex)));
                    break;
                }
                let bestIndex = -1;
                let bestTerm = null;

                for (const term of normalizedTerms) {
                    const idx = originalLower.indexOf(term.lower, startIndex);
                    if (idx !== -1 && (bestIndex === -1 || idx < bestIndex)) {
                        bestIndex = idx;
                        bestTerm = term;
                    }
                }

                if (bestIndex === -1 || !bestTerm) {
                    fragment.appendChild(document.createTextNode(original.slice(startIndex)));
                    break;
                }

                if (bestIndex > startIndex) {
                    fragment.appendChild(document.createTextNode(original.slice(startIndex, bestIndex)));
                }

                const matched = original.slice(bestIndex, bestIndex + bestTerm.raw.length);
                const mark = document.createElement('mark');
                mark.className = 'document-preview-highlight';
                mark.textContent = matched;
                fragment.appendChild(mark);
                replaced = true;
                highlightedCount += 1;

                startIndex = bestIndex + bestTerm.raw.length;
            }

            if (replaced && node.parentNode) {
                node.parentNode.replaceChild(fragment, node);
            }
        });
        return highlightedCount;
    },

    /**
     * 标准化文本，便于匹配定位
     * @param {string} value - 原始文本
     * @returns {string}
     */
    normalizeText(value) {
        return String(value || '')
            .replace(/\s+/g, ' ')
            .trim();
    },

    /**
     * 转义 HTML
     * @param {string} value - 原始值
     * @returns {string}
     */
    escapeHtml(value) {
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    },

    /**
     * 转义属性值
     * @param {string} value - 原始值
     * @returns {string}
     */
    escapeAttribute(value) {
        return this.escapeHtml(value);
    },
};

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { DocumentPreview };
}
