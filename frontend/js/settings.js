/**
 * RAG 知识库助手 - 系统设置模块
 * 
 * 处理系统设置页面的所有交互逻辑
 */

/**
 * 系统设置模块
 */
const SettingsModule = {
    elements: {},
    state: {
        settings: null,
        models: { llm_models: [], embedding_models: [] },
        stats: null,
        readOnlyKeys: [
            'app_name',
            'app_version',
            'debug',
            'data_dir',
            'upload_dir',
            'chroma_persist_dir',
            'db_path',
        ],
    },
    /**
     * 页面进入回调
     */
    onEnter() {
        console.log('Settings page entered');
        this.renderSettingsPage();
        this.bindEvents();
        this.loadSettingsData();
    },

    /**
     * 渲染设置页面
     */
    renderSettingsPage() {
        const pageSection = document.getElementById('page-settings');
        if (!pageSection) return;

        pageSection.innerHTML = `
            <div class="settings-page">
                <div class="page-header">
                    <div class="page-header-main">
                        <div class="page-header-copy">
                            <h1 class="page-title">系统设置</h1>
                            <p class="page-description">集中管理模型、检索参数与运行环境配置。</p>
                        </div>
                        <button type="button" class="btn btn-secondary" id="refresh-settings-btn">刷新数据</button>
                    </div>
                </div>

                <form class="settings-form" id="settings-form">
                    <div class="settings-section">
                        <div class="settings-section-header">
                            <div>
                                <h2 class="settings-section-title">API 配置</h2>
                                <p class="settings-section-description">配置大模型与向量服务的访问地址和密钥。</p>
                            </div>
                        </div>
                        <div class="settings-section-body">
                            <div class="settings-card-grid">
                                <div class="settings-card">
                                    <div class="settings-card-header">
                                        <div>
                                            <h3 class="settings-card-title">OpenAI 服务</h3>
                                            <p class="settings-card-description">用于问答生成的主模型服务。</p>
                                        </div>
                                        <span class="badge badge-neutral">必填基础配置</span>
                                    </div>
                                    <div class="form-group">
                                        <label class="form-label" for="openai-base-url">接口地址</label>
                                        <div class="form-caption">推荐使用兼容 OpenAI 规范的 API 地址。</div>
                                        <input class="form-input" type="text" id="openai-base-url" name="openai_base_url" placeholder="https://api.openai.com/v1">
                                        <div class="form-hint">示例：https://api.openai.com/v1</div>
                                    </div>
                                    <div class="form-group form-group-compact">
                                        <div class="form-label-row">
                                            <label class="form-label" for="openai-api-key">API Key</label>
                                            <span class="badge" id="openai-key-state">未配置</span>
                                        </div>
                                        <div class="form-caption">出于安全考虑，已保存的密钥不会回显。</div>
                                        <input class="form-input" type="password" id="openai-api-key" name="openai_api_key" placeholder="留空表示保持当前配置">
                                        <div class="form-hint">仅在需要替换密钥时重新输入。</div>
                                    </div>
                                </div>

                                <div class="settings-card">
                                    <div class="settings-card-header">
                                        <div>
                                            <h3 class="settings-card-title">Embedding 服务</h3>
                                            <p class="settings-card-description">用于向量化检索，可与主模型服务分开配置。</p>
                                        </div>
                                        <span class="badge badge-neutral">可选独立配置</span>
                                    </div>
                                    <div class="form-group">
                                        <label class="form-label" for="embedding-base-url">接口地址</label>
                                        <div class="form-caption">如留空，默认跟随 OpenAI 服务地址。</div>
                                        <input class="form-input" type="text" id="embedding-base-url" name="embedding_base_url" placeholder="默认继承 OpenAI 服务地址">
                                        <div class="form-hint">适合接入独立向量化服务时单独配置。</div>
                                    </div>
                                    <div class="form-group form-group-compact">
                                        <div class="form-label-row">
                                            <label class="form-label" for="embedding-api-key">API Key</label>
                                            <span class="badge" id="embedding-key-state">未配置</span>
                                        </div>
                                        <div class="form-caption">如为空，则沿用当前已保存的密钥。</div>
                                        <input class="form-input" type="password" id="embedding-api-key" name="embedding_api_key" placeholder="留空表示保持当前配置">
                                        <div class="form-hint">可与主模型共用，也可独立配置。</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="settings-section">
                        <div class="settings-section-header">
                            <div>
                                <h2 class="settings-section-title">模型配置</h2>
                                <p class="settings-section-description">选择问答模型与向量模型。</p>
                            </div>
                        </div>
                        <div class="settings-section-body">
                            <div class="form-group">
                                <label class="form-label" for="llm-model">问答模型</label>
                                <div class="form-caption">控制生成回答的质量、速度与成本。</div>
                                <select class="form-select" id="llm-model" name="llm_model">
                                    <option value="">加载中...</option>
                                </select>
                                <div class="form-hint">默认推荐 GPT-4o Mini，适合日常问答场景。</div>
                            </div>
                            <div class="form-group form-group-compact">
                                <label class="form-label" for="embedding-model">向量模型</label>
                                <div class="form-caption">决定文本向量化效果，直接影响召回质量。</div>
                                <select class="form-select" id="embedding-model" name="embedding_model">
                                    <option value="">加载中...</option>
                                </select>
                                <div class="form-hint">如无特殊需求，保持默认配置即可。</div>
                            </div>
                        </div>
                    </div>

                    <div class="settings-section">
                        <div class="settings-section-header">
                            <div>
                                <h2 class="settings-section-title">生成参数</h2>
                                <p class="settings-section-description">控制回答风格、长度与稳定性。</p>
                            </div>
                        </div>
                        <div class="settings-section-body">
                            <div class="form-grid">
                                <div class="form-group">
                                    <label class="form-label" for="llm-temperature">随机性（Temperature）</label>
                                    <div class="form-caption">数值越低越稳定，越高越发散。</div>
                                    <input class="form-input" type="number" id="llm-temperature" name="llm_temperature" min="0" max="2" step="0.1">
                                    <div class="form-hint">推荐范围 0.2 - 0.8。</div>
                                </div>
                                <div class="form-group">
                                    <label class="form-label" for="llm-max-tokens">最大输出长度</label>
                                    <div class="form-caption">限制单次回答生成的最大 Token 数。</div>
                                    <input class="form-input" type="number" id="llm-max-tokens" name="llm_max_tokens" min="1" max="8192" step="1">
                                    <div class="form-hint">数值越大，回答越长，但成本也更高。</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="settings-section">
                        <div class="settings-section-header">
                            <div>
                                <h2 class="settings-section-title">检索配置</h2>
                                <p class="settings-section-description">控制召回范围与过滤强度。</p>
                            </div>
                        </div>
                        <div class="settings-section-body">
                            <div class="form-grid">
                                <div class="form-group">
                                    <label class="form-label" for="default-top-k">召回数量（Top-K）</label>
                                    <div class="form-caption">每次从知识库中取回多少条候选片段。</div>
                                    <input class="form-input" type="number" id="default-top-k" name="default_top_k" min="1" max="20" step="1">
                                    <div class="form-hint">一般设置为 3 - 8 较合适。</div>
                                </div>
                                <div class="form-group">
                                    <label class="form-label" for="similarity-threshold">相似度阈值</label>
                                    <div class="form-caption">过滤低相关内容，提升回答聚焦度。</div>
                                    <input class="form-input" type="number" id="similarity-threshold" name="similarity_threshold" min="0" max="1" step="0.05">
                                    <div class="form-hint">若召回不足，可适当降低该值。</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="settings-section">
                        <div class="settings-section-header">
                            <div>
                                <h2 class="settings-section-title">文本分块</h2>
                                <p class="settings-section-description">影响文档切分粒度和检索上下文连续性。</p>
                            </div>
                        </div>
                        <div class="settings-section-body">
                            <div class="form-grid">
                                <div class="form-group">
                                    <label class="form-label" for="chunk-size">分块大小</label>
                                    <div class="form-caption">单个文本块包含的字符数。</div>
                                    <input class="form-input" type="number" id="chunk-size" name="chunk_size" min="100" max="2000" step="10">
                                    <div class="form-hint">块越大，上下文更完整，但可能降低检索精度。</div>
                                </div>
                                <div class="form-group">
                                    <label class="form-label" for="chunk-overlap">分块重叠</label>
                                    <div class="form-caption">相邻文本块共享的字符数。</div>
                                    <input class="form-input" type="number" id="chunk-overlap" name="chunk_overlap" min="0" max="500" step="10">
                                    <div class="form-hint">建议小于分块大小，并保持适度重叠。</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="settings-section">
                        <div class="settings-section-header">
                            <div>
                                <h2 class="settings-section-title">系统信息</h2>
                                <p class="settings-section-description">查看当前知识库规模与运行环境。</p>
                            </div>
                        </div>
                        <div class="settings-section-body">
                            <div class="settings-stats" id="settings-stats">
                                <div class="settings-stat">
                                    <div class="settings-stat-value" id="stat-docs">0</div>
                                    <div class="settings-stat-label">已收录文档</div>
                                </div>
                                <div class="settings-stat">
                                    <div class="settings-stat-value" id="stat-chunks">0</div>
                                    <div class="settings-stat-label">文本分块</div>
                                </div>
                                <div class="settings-stat">
                                    <div class="settings-stat-value" id="stat-messages">0</div>
                                    <div class="settings-stat-label">累计消息</div>
                                </div>
                            </div>
                            <div class="readonly-header">
                                <h3 class="readonly-title">运行环境</h3>
                                <p class="readonly-description">以下信息仅用于展示，不能直接在页面修改。</p>
                            </div>
                            <div class="settings-readonly" id="settings-readonly"></div>
                        </div>
                    </div>

                    <div class="settings-actions">
                        <div class="settings-actions-hint">保存后会同步更新服务器当前配置。</div>
                        <div class="settings-actions-buttons">
                            <button type="button" class="btn btn-secondary" id="reset-settings-btn">恢复默认参数</button>
                            <button type="submit" class="btn btn-primary" id="save-settings-btn">保存设置</button>
                        </div>
                    </div>
                </form>
            </div>
        `;
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        const form = document.getElementById('settings-form');
        const resetBtn = document.getElementById('reset-settings-btn');
        const refreshBtn = document.getElementById('refresh-settings-btn');

        form?.addEventListener('submit', (event) => {
            event.preventDefault();
            this.handleSave();
        });

        resetBtn?.addEventListener('click', () => {
            this.handleReset();
        });

        refreshBtn?.addEventListener('click', () => {
            this.loadSettingsData();
        });
    },

    /**
     * 加载设置、模型与统计数据
     */
    async loadSettingsData() {
        const loader = Loading.show('加载系统设置...');
        try {
            const [settingsRes, modelsRes, statsRes] = await Promise.all([
                api.getSettings(),
                api.getAvailableModels(),
                api.getSystemStats(),
            ]);

            this.state.settings = settingsRes?.data || null;
            this.state.models = modelsRes?.data || { llm_models: [], embedding_models: [] };
            this.state.stats = statsRes?.data || null;

            this.fillFormValues();
            this.renderApiKeyState();
            this.renderReadonlyInfo();
            this.renderStats();
        } catch (error) {
            console.error('Load settings error:', error);
            Toast.error(error.message || '加载设置失败');
        } finally {
            loader.close();
        }
    },

    /**
     * 填充表单值
     */
    fillFormValues() {
        const settings = this.state.settings;
        if (!settings) return;

        this.renderModelOptions();

        this.setInputValue('llm-model', settings.llm_model);
        this.setInputValue('embedding-model', settings.embedding_model);
        this.setInputValue('llm-temperature', settings.llm_temperature);
        this.setInputValue('llm-max-tokens', settings.llm_max_tokens);
        this.setInputValue('default-top-k', settings.default_top_k);
        this.setInputValue('similarity-threshold', settings.similarity_threshold);
        this.setInputValue('chunk-size', settings.chunk_size);
        this.setInputValue('chunk-overlap', settings.chunk_overlap);

        const baseUrlInput = document.getElementById('openai-base-url');
        if (baseUrlInput) baseUrlInput.value = settings.openai_base_url || '';

        const embeddingBaseInput = document.getElementById('embedding-base-url');
        if (embeddingBaseInput) {
            const embeddingUrl = settings.embedding_base_url || '';
            const openaiUrl = settings.openai_base_url || '';
            embeddingBaseInput.value = embeddingUrl && embeddingUrl !== openaiUrl ? embeddingUrl : '';
        }
    },

    /**
     * 渲染模型选项
     */
    renderModelOptions() {
        const llmSelect = document.getElementById('llm-model');
        const embedSelect = document.getElementById('embedding-model');
        if (!llmSelect || !embedSelect) return;

        const llmModels = this.state.models?.llm_models || [];
        const embeddingModels = this.state.models?.embedding_models || [];

        llmSelect.innerHTML = llmModels.length
            ? llmModels.map(model => `
                <option value="${model.id}">${model.name}</option>
            `).join('')
            : '<option value="">暂无可用模型</option>';

        embedSelect.innerHTML = embeddingModels.length
            ? embeddingModels.map(model => `
                <option value="${model.id}">${model.name}</option>
            `).join('')
            : '<option value="">暂无可用模型</option>';
    },

    /**
     * 渲染 API Key 状态
     */
    renderApiKeyState() {
        const settings = this.state.settings;
        if (!settings) return;

        const openaiState = document.getElementById('openai-key-state');
        const embeddingState = document.getElementById('embedding-key-state');

        if (openaiState) {
            openaiState.textContent = settings.has_openai_api_key ? '已配置' : '未配置';
            openaiState.classList.toggle('badge-success', settings.has_openai_api_key);
            openaiState.classList.toggle('badge-warning', !settings.has_openai_api_key);
        }

        if (embeddingState) {
            embeddingState.textContent = settings.has_embedding_api_key ? '已配置' : '未配置';
            embeddingState.classList.toggle('badge-success', settings.has_embedding_api_key);
            embeddingState.classList.toggle('badge-warning', !settings.has_embedding_api_key);
        }
    },

    /**
     * 渲染只读信息
     */
    renderReadonlyInfo() {
        const container = document.getElementById('settings-readonly');
        const settings = this.state.settings;
        if (!container || !settings) return;

        const items = this.state.readOnlyKeys
            .filter(key => settings[key] !== undefined)
            .map(key => ({
                label: this.getReadonlyLabel(key),
                value: settings[key],
            }));

        container.innerHTML = items.map(item => `
            <div class="readonly-item">
                <div class="readonly-label">${item.label}</div>
                <div class="readonly-value">${item.value}</div>
            </div>
        `).join('');
    },

    /**
     * 渲染统计信息
     */
    renderStats() {
        const stats = this.state.stats;
        if (!stats) return;

        const docValue = document.getElementById('stat-docs');
        const chunkValue = document.getElementById('stat-chunks');
        const msgValue = document.getElementById('stat-messages');

        if (docValue) docValue.textContent = stats.documents?.total ?? 0;
        if (chunkValue) chunkValue.textContent = stats.documents?.total_chunks ?? 0;
        if (msgValue) msgValue.textContent = stats.conversations?.total_messages ?? 0;
    },

    /**
     * 处理保存
     */
    async handleSave() {
        if (!this.validateForm()) return;

        const openaiApiKey = this.getInputValue('openai-api-key').trim();
        const embeddingApiKey = this.getInputValue('embedding-api-key').trim();
        const openaiBaseUrlRaw = this.getInputValue('openai-base-url').trim();
        const embeddingBaseUrlRaw = this.getInputValue('embedding-base-url').trim();

        const openaiBaseUrl = openaiBaseUrlRaw === '' ? null : openaiBaseUrlRaw;
        const embeddingBaseUrl = embeddingBaseUrlRaw === '' ? null : embeddingBaseUrlRaw;

        const payload = {
            openai_base_url: openaiBaseUrl,
            embedding_base_url: embeddingBaseUrl,
            llm_model: this.getInputValue('llm-model'),
            embedding_model: this.getInputValue('embedding-model'),
            llm_temperature: this.getNumberValue('llm-temperature'),
            llm_max_tokens: this.getNumberValue('llm-max-tokens'),
            default_top_k: this.getNumberValue('default-top-k'),
            similarity_threshold: this.getNumberValue('similarity-threshold'),
            chunk_size: this.getNumberValue('chunk-size'),
            chunk_overlap: this.getNumberValue('chunk-overlap'),
        };

        if (openaiApiKey) payload.openai_api_key = openaiApiKey;
        if (embeddingApiKey) payload.embedding_api_key = embeddingApiKey;

        Object.keys(payload).forEach((key) => {
            if (payload[key] === '' || Number.isNaN(payload[key])) {
                delete payload[key];
            }
        });

        const btn = document.getElementById('save-settings-btn');
        const loader = Loading.button(btn, '保存中...');

        try {
            const result = await api.updateSettings(payload);
            const message = result?.message || '设置已保存';
            Toast.success(message);
            this.state.settings = result?.data || this.state.settings;
            this.renderApiKeyState();
        } catch (error) {
            console.error('Save settings error:', error);
            Toast.error(error.message || '保存失败');
        } finally {
            loader.close();
        }
    },

    /**
     * 处理重置
     */
    async handleReset() {
        const confirmed = await ConfirmDialog.show({
            title: '重置设置',
            message: '确定要将设置重置为默认值吗？此操作将覆盖当前 .env 配置。',
            confirmText: '重置',
            cancelText: '取消',
            type: 'warning',
        });

        if (!confirmed) return;

        const defaults = this.state.settings?.defaults;
        if (!defaults) {
            Toast.warning('未获取到默认配置，无法重置');
            return;
        }

        const payload = {
            openai_base_url: defaults.openai_base_url,
            embedding_base_url: defaults.embedding_base_url,
            llm_model: defaults.llm_model,
            embedding_model: defaults.embedding_model,
            default_top_k: defaults.default_top_k,
            chunk_size: defaults.chunk_size,
            chunk_overlap: defaults.chunk_overlap,
            max_chat_history: defaults.max_chat_history,
            llm_temperature: defaults.llm_temperature,
            llm_max_tokens: defaults.llm_max_tokens,
            similarity_threshold: defaults.similarity_threshold,
        };

        const btn = document.getElementById('reset-settings-btn');
        const loader = Loading.button(btn, '重置中...');

        try {
            const result = await api.updateSettings(payload);
            Toast.success(result?.message || '已重置为默认值');
            this.state.settings = result?.data || this.state.settings;
            this.fillFormValues();
            this.renderApiKeyState();
        } catch (error) {
            console.error('Reset settings error:', error);
            Toast.error(error.message || '重置失败');
        } finally {
            loader.close();
        }
    },

    /**
     * 表单校验
     */
    validateForm() {
        const openaiBaseUrl = this.getInputValue('openai-base-url');
        if (openaiBaseUrl && !this.isValidUrl(openaiBaseUrl)) {
            Toast.error('OpenAI Base URL 格式不正确');
            return false;
        }

        const embeddingBaseUrl = this.getInputValue('embedding-base-url');
        if (embeddingBaseUrl && !this.isValidUrl(embeddingBaseUrl)) {
            Toast.error('Embedding Base URL 格式不正确');
            return false;
        }

        const chunkSize = this.getNumberValue('chunk-size');
        const chunkOverlap = this.getNumberValue('chunk-overlap');
        if (chunkOverlap >= chunkSize) {
            Toast.error('分块重叠必须小于分块大小');
            return false;
        }

        return true;
    },

    /**
     * 获取表单值
     */
    getInputValue(id) {
        const element = document.getElementById(id);
        return element ? element.value : '';
    },

    /**
     * 获取数字值
     */
    getNumberValue(id) {
        const value = this.getInputValue(id);
        if (value === '') return null;
        return Number(value);
    },

    /**
     * 设置表单值
     */
    setInputValue(id, value) {
        const element = document.getElementById(id);
        if (!element || value === undefined || value === null) return;
        element.value = value;
    },

    /**
     * 校验 URL
     */
    isValidUrl(url) {
        try {
            const parsed = new URL(url);
            return parsed.protocol === 'http:' || parsed.protocol === 'https:';
        } catch (error) {
            return false;
        }
    },

    /**
     * 只读字段标签
     */
    getReadonlyLabel(key) {
        const labels = {
            app_name: '应用名称',
            app_version: '应用版本',
            debug: '调试模式',
            data_dir: '数据目录',
            upload_dir: '上传目录',
            chroma_persist_dir: '向量库目录',
            db_path: '数据库路径',
        };

        return labels[key] || key;
    }
};

// 导出（如果支持模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SettingsModule };
}
