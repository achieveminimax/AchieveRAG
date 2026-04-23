/**
 * RAG 知识库助手 - 应用入口
 *
 * 负责：
 * - 全局状态管理（订阅/发布模式）
 * - 基于 hash 的路由管理
 * - 页面初始化与模块协调
 * - 侧边栏导航交互
 */

// ==================== 全局状态管理 ====================

/**
 * 全局状态管理器
 * 使用订阅/发布模式实现状态管理
 */
const AppState = {
    // 状态数据
    _state: {
        currentConversationId: null,
        isGenerating: false,
        documents: [],
        conversations: [],
        currentPage: 'chat'
    },

    // 订阅者映射
    _subscribers: {},

    /**
     * 获取状态值
     * @param {string} key - 状态键名
     * @returns {any}
     */
    get(key) {
        return this._state[key];
    },

    /**
     * 设置状态值
     * @param {string} key - 状态键名
     * @param {any} value - 状态值
     */
    set(key, value) {
        const oldValue = this._state[key];
        this._state[key] = value;

        // 通知订阅者
        this._notify(key, value, oldValue);
    },

    /**
     * 批量设置状态
     * @param {Object} updates - 状态更新对象
     */
    batchSet(updates) {
        Object.entries(updates).forEach(([key, value]) => {
            this.set(key, value);
        });
    },

    /**
     * 订阅状态变化
     * @param {string} key - 状态键名
     * @param {Function} callback - 回调函数 (newValue, oldValue) => void
     * @returns {Function} - 取消订阅函数
     */
    subscribe(key, callback) {
        if (!this._subscribers[key]) {
            this._subscribers[key] = [];
        }

        this._subscribers[key].push(callback);

        // 返回取消订阅函数
        return () => {
            this._subscribers[key] = this._subscribers[key].filter(cb => cb !== callback);
        };
    },

    /**
     * 订阅多个状态变化
     * @param {string[]} keys - 状态键名数组
     * @param {Function} callback - 回调函数 (state) => void
     * @returns {Function} - 取消订阅函数
     */
    subscribeMultiple(keys, callback) {
        const unsubscribes = keys.map(key => this.subscribe(key, () => {
            callback(this._state);
        }));

        return () => unsubscribes.forEach(unsub => unsub());
    },

    /**
     * 通知订阅者
     * @private
     */
    _notify(key, newValue, oldValue) {
        const subscribers = this._subscribers[key];
        if (subscribers) {
            subscribers.forEach(callback => {
                try {
                    callback(newValue, oldValue);
                } catch (error) {
                    console.error(`State subscriber error for key "${key}":`, error);
                }
            });
        }
    },

    /**
     * 获取当前所有状态
     * @returns {Object}
     */
    getAll() {
        return { ...this._state };
    },

    /**
     * 重置状态
     */
    reset() {
        this._state = {
            currentConversationId: null,
            isGenerating: false,
            documents: [],
            conversations: [],
            currentPage: 'chat'
        };
    }
};


// ==================== 路由管理 ====================

/**
 * 路由管理器
 * 基于 URL hash 实现前端路由
 */
const Router = {
    // 路由配置
    routes: {
        'chat': { page: 'chat', title: '智能问答' },
        'upload': { page: 'upload', title: '知识库管理' },
        'history': { page: 'history', title: '对话历史' },
        'settings': { page: 'settings', title: '系统设置' }
    },

    // 当前路由
    currentRoute: null,

    // 路由守卫
    beforeEach: null,

    /**
     * 初始化路由
     */
    init() {
        // 监听 hash 变化
        window.addEventListener('hashchange', () => this._handleRouteChange());

        // 处理初始路由
        this._handleRouteChange();
    },

    /**
     * 导航到指定路由
     * @param {string} path - 路由路径
     */
    push(path) {
        if (path.startsWith('#')) {
            path = path.slice(1);
        }
        window.location.hash = path;
    },

    /**
     * 替换当前路由
     * @param {string} path - 路由路径
     */
    replace(path) {
        if (path.startsWith('#')) {
            path = path.slice(1);
        }
        window.location.replace(`#${path}`);
    },

    /**
     * 获取当前路由
     * @returns {string}
     */
    getCurrentRoute() {
        const hash = window.location.hash.slice(1) || 'chat';
        return hash.split('/')[0];
    },

    /**
     * 处理路由变化
     * @private
     */
    _handleRouteChange() {
        const hash = window.location.hash.slice(1) || 'chat';
        const routeName = hash.split('/')[0];
        const routeParams = hash.split('/').slice(1);

        const route = this.routes[routeName];

        if (!route) {
            console.warn(`Unknown route: ${routeName}`);
            this.push('chat');
            return;
        }

        // 路由守卫
        if (this.beforeEach) {
            const canProceed = this.beforeEach(routeName, this.currentRoute);
            if (canProceed === false) {
                return;
            }
        }

        // 更新当前路由
        const prevRoute = this.currentRoute;
        this.currentRoute = routeName;

        // 更新页面标题
        document.title = `${route.title} - RAG 知识库助手`;

        // 更新 UI
        this._updateUI(routeName, routeParams);

        // 触发路由进入事件
        this._onRouteEnter(routeName, routeParams, prevRoute);
    },

    /**
     * 更新 UI
     * @private
     */
    _updateUI(routeName, params) {
        // 更新侧边栏导航
        this._updateSidebar(routeName);

        // 更新页面显示
        this._updatePage(routeName);

        // 更新全局状态
        AppState.set('currentPage', routeName);
    },

    /**
     * 更新侧边栏导航
     * @private
     */
    _updateSidebar(activeRoute) {
        const navItems = document.querySelectorAll('.sidebar-nav-item');

        navItems.forEach(item => {
            const page = item.dataset.page;
            if (page === activeRoute) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
    },

    /**
     * 更新页面显示
     * @private
     */
    _updatePage(activeRoute) {
        const pages = document.querySelectorAll('.page-section');

        pages.forEach(page => {
            const pageId = page.id.replace('page-', '');
            if (pageId === activeRoute) {
                page.classList.add('active');
            } else {
                page.classList.remove('active');
            }
        });
    },

    /**
     * 路由进入回调
     * @private
     */
    _onRouteEnter(routeName, params, prevRoute) {
        // 触发页面特定的初始化
        switch (routeName) {
            case 'chat':
                // 对话页面已在初始化时加载
                break;
            case 'upload':
                if (typeof UploadModule !== 'undefined') {
                    UploadModule.onEnter?.();
                }
                break;
            case 'history':
                if (typeof HistoryModule !== 'undefined') {
                    HistoryModule.onEnter?.();
                }
                break;
            case 'settings':
                if (typeof SettingsModule !== 'undefined') {
                    SettingsModule.onEnter?.();
                }
                break;
        }

        // 触发自定义事件
        window.dispatchEvent(new CustomEvent('routechange', {
            detail: { route: routeName, params, prevRoute }
        }));
    }
};


// ==================== 应用初始化 ====================

/**
 * 应用主对象
 */
const App = {
    /**
     * 初始化应用
     */
    init() {
        console.log('RAG Knowledge Assistant initializing...');
        
        // 检查 marked.js
        if (typeof marked !== 'undefined') {
            console.log('[App] marked.js 已加载, 版本:', marked.VERSION || '未知');
        } else {
            console.warn('[App] marked.js 未加载, Markdown 渲染将降级为纯文本');
        }

        // 初始化路由守卫
        this._initRouteGuard();

        // 初始化路由
        Router.init();

        // 初始化侧边栏
        this._initSidebar();

        // 初始化各模块
        this._initModules();

        // 初始化全局事件
        this._initGlobalEvents();
        this._initStateSubscriptions();
        this._initSidebarConversations();

        const chatNewChatBtn = document.getElementById('chat-new-chat-btn');
        chatNewChatBtn?.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.newChat();
        });

        // 加载初始数据
        this._loadInitialData();

        console.log('RAG Knowledge Assistant initialized');
    },

    /**
     * 初始化路由守卫
     * @private
     */
    _initRouteGuard() {
        Router.beforeEach = (to, from) => {
            // 如果正在生成回答，提示用户
            if (AppState.get('isGenerating') && to !== from) {
                Toast.warning('AI 正在回答中，请稍后再切换页面');
                return false;
            }
            return true;
        };
    },

    /**
     * 初始化侧边栏
     * @private
     */
    _initSidebar() {
        const navItems = document.querySelectorAll('.sidebar-nav-item');

        navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const page = item.dataset.page;
                if (page) {
                    Router.push(page);
                }
            });
        });
    },

    _sidebarConv: {
        initialized: false,
        elements: {
            container: null,
            empty: null,
            list: null,
            newChatBtn: null,
            openHistoryBtn: null,
        },
        maxItems: 8,
        onDelete: null,
    },

    _initSidebarConversations() {
        if (this._sidebarConv.initialized) return;

        const container = document.getElementById('sidebar-conv');
        const empty = document.getElementById('sidebar-conv-empty');
        const list = document.getElementById('sidebar-conv-list');
        const newChatBtn = document.getElementById('sidebar-new-chat-btn');
        const openHistoryBtn = document.getElementById('sidebar-open-history-btn');

        if (!container || !empty || !list) return;

        this._sidebarConv.elements = {
            container,
            empty,
            list,
            newChatBtn,
            openHistoryBtn,
        };

        newChatBtn?.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.newChat();
        });

        openHistoryBtn?.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            Router.push('history');
        });

        this._sidebarConv.onDelete = async (conversation) => {
            const ok = await ConfirmDialog.delete(conversation.title || '此对话');
            if (!ok) return;

            try {
                await api.deleteConversation(conversation.id);

                const currentId = AppState.get('currentConversationId');
                if (currentId && currentId === conversation.id) {
                    this.newChat();
                }

                const resp = await api.getConversations();
                const conversations = resp?.data?.conversations || [];
                AppState.set('conversations', conversations);
            } catch (e) {
                Toast.error('删除失败');
            }
        };

        AppState.subscribeMultiple(['conversations', 'currentConversationId'], (state) => {
            this._renderSidebarConversations(state.conversations || [], state.currentConversationId);
        });

        this._renderSidebarConversations(AppState.get('conversations') || [], AppState.get('currentConversationId'));

        this._sidebarConv.initialized = true;
    },

    _renderSidebarConversations(conversations, currentId) {
        const { empty, list } = this._sidebarConv.elements || {};
        if (!empty || !list) return;

        const items = Array.isArray(conversations) ? conversations.slice(0, this._sidebarConv.maxItems) : [];

        list.innerHTML = '';

        if (items.length === 0) {
            empty.classList.remove('hidden');
            return;
        }

        empty.classList.add('hidden');

        items.forEach((conv) => {
            const itemEl = document.createElement('button');
            itemEl.className = 'sidebar-conv-item';
            itemEl.type = 'button';
            itemEl.dataset.conversationId = conv.id;
            if (currentId && conv.id === currentId) {
                itemEl.classList.add('active');
            }

            const dotEl = document.createElement('span');
            dotEl.className = 'sidebar-conv-item-dot';
            dotEl.setAttribute('aria-hidden', 'true');

            const contentEl = document.createElement('div');
            contentEl.className = 'sidebar-conv-item-content';

            const titleEl = document.createElement('div');
            titleEl.className = 'sidebar-conv-item-title';
            titleEl.textContent = conv.title || '未命名对话';

            const metaEl = document.createElement('div');
            metaEl.className = 'sidebar-conv-item-meta';
            const ts = conv.updated_at || conv.created_at;
            const timeText = this._formatConversationTime(ts);
            const count = Number.isFinite(conv.message_count) ? conv.message_count : (conv.message_count || 0);
            metaEl.textContent = `${count} 条消息${timeText ? ` · ${timeText}` : ''}`;

            contentEl.appendChild(titleEl);
            contentEl.appendChild(metaEl);

            itemEl.appendChild(dotEl);
            itemEl.appendChild(contentEl);

            itemEl.addEventListener('click', () => {
                this.loadConversation(conv.id);
            });

            list.appendChild(itemEl);
        });
    },

    _formatConversationTime(ts) {
        if (!ts) return '';
        const date = ts instanceof Date ? ts : new Date(ts);
        if (Number.isNaN(date.getTime())) return '';
        return date.toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit',
            hour12: false,
            timeZone: 'Asia/Shanghai',
        });
    },

    /**
     * 初始化各模块
     * @private
     */
    _initModules() {
        // 初始化对话模块
        if (typeof ChatModule !== 'undefined') {
            ChatModule.init();
        }

        // 其他模块在路由进入时初始化
    },

    /**
     * 初始化全局事件
     * @private
     */
    _initGlobalEvents() {
        // 键盘快捷键
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + K 聚焦输入框
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                const input = document.getElementById('chat-input');
                if (input && AppState.get('currentPage') === 'chat') {
                    input.focus();
                }
            }

            // ESC 取消生成
            if (e.key === 'Escape' && AppState.get('isGenerating')) {
                // 触发取消生成事件
                window.dispatchEvent(new CustomEvent('cancelGeneration'));
            }
        });

        // 页面可见性变化
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                // 页面重新可见时刷新数据
                this._refreshData();
            }
        });

        // 在线/离线状态
        window.addEventListener('online', () => {
            Toast.success('网络已连接');
        });

        window.addEventListener('offline', () => {
            Toast.warning('网络已断开，部分功能可能不可用');
        });
    },

    /**
     * 初始化状态订阅
     * @private
     */
    _initStateSubscriptions() {
        AppState.subscribe('documents', () => {
            if (typeof ChatModule !== 'undefined' && typeof ChatModule._updateDocumentSelector === 'function') {
                ChatModule._updateDocumentSelector();
            }
        });
    },

    /**
     * 加载初始数据
     * @private
     */
    async _loadInitialData() {
        try {
            // 加载文档列表
            const docsResponse = await api.getDocuments();
            if (docsResponse?.data) {
                AppState.set('documents', docsResponse.data);
            }

            // 加载对话列表
            const convResponse = await api.getConversations();
            if (convResponse?.data) {
                const conversations = convResponse.data?.conversations || [];
                AppState.set('conversations', conversations);
            }
        } catch (error) {
            console.error('Failed to load initial data:', error);
        }
    },

    /**
     * 刷新数据
     * @private
     */
    async _refreshData() {
        // 根据当前页面刷新相应数据
        const currentPage = AppState.get('currentPage');

        try {
            switch (currentPage) {
                case 'upload':
                    const docsResponse = await api.getDocuments();
                    if (docsResponse?.data) {
                        AppState.set('documents', docsResponse.data);
                    }
                    break;
                case 'history':
                    const convResponse = await api.getConversations();
                    if (convResponse?.data) {
                        const conversations = convResponse.data?.conversations || [];
                        AppState.set('conversations', conversations);
                    }
                    break;
            }
        } catch (error) {
            console.error('Failed to refresh data:', error);
        }
    },

    /**
     * 新建对话
     */
    newChat() {
        // 重置当前对话 ID
        AppState.set('currentConversationId', null);

        // 清空对话界面
        if (typeof ChatModule !== 'undefined') {
            ChatModule.newChat();
        }

        // 导航到对话页面
        Router.push('chat');

        Toast.success('已开始新对话');
    },

    /**
     * 加载指定对话
     * @param {string} conversationId - 对话 ID
     */
    async loadConversation(conversationId) {
        try {
            Loading.show('加载对话中...');

            const response = await api.getConversation(conversationId);

            if (response?.data) {
                // 设置当前对话 ID
                AppState.set('currentConversationId', conversationId);

                // 加载对话消息
                if (typeof ChatModule !== 'undefined' && response.data.messages) {
                    ChatModule.loadConversation(response.data.messages);
                }

                // 导航到对话页面
                Router.push('chat');
            }
        } catch (error) {
            Toast.error('加载对话失败');
            console.error('Failed to load conversation:', error);
        } finally {
            Loading.close();
        }
    }
};


// ==================== DOM 加载完成后初始化 ====================

document.addEventListener('DOMContentLoaded', () => {
    App.init();
});


// ==================== 导出（如果支持模块系统） ====================

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AppState, Router, App };
}
