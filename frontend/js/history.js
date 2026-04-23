const HistoryModule = {
    onEnter() {
        this._initOnce();
        this.refresh();
    },

    _initialized: false,
    _unsubscribe: null,
    elements: {
        list: null,
        empty: null,
        content: null,
        newChatBtn: null,
        emptyNewChatBtn: null,
        deleteAllBtn: null,
    },

    _initOnce() {
        if (this._initialized) return;

        this.elements.list = document.getElementById('history-list');
        this.elements.empty = document.getElementById('history-empty');
        this.elements.content = document.getElementById('history-content');
        this.elements.newChatBtn = document.getElementById('history-new-chat-btn');
        this.elements.emptyNewChatBtn = document.getElementById('history-empty-new-chat-btn');
        this.elements.deleteAllBtn = document.getElementById('history-delete-all-btn');

        this.elements.newChatBtn?.addEventListener('click', () => {
            App?.newChat?.();
        });

        this.elements.emptyNewChatBtn?.addEventListener('click', () => {
            App?.newChat?.();
        });

        this.elements.deleteAllBtn?.addEventListener('click', async () => {
            const ok = await ConfirmDialog.show({
                title: '删除全部对话',
                message: '将删除全部对话及其消息记录，此操作不可撤销。',
                confirmText: '删除全部',
                cancelText: '取消',
                type: 'danger'
            });
            if (!ok) return;

            const loader = Loading.attach(this.elements.content, '删除中...');
            try {
                await api.deleteAllConversations();
                AppState.set('currentConversationId', null);
                AppState.set('conversations', []);
                this._render([]);
            } catch (e) {
                Toast.error('删除失败');
            } finally {
                loader.close();
            }
        });

        this._unsubscribe = AppState.subscribe('conversations', (conversations) => {
            this._render(conversations || []);
        });

        this._initialized = true;
    },

    async refresh() {
        const loader = Loading.attach(this.elements.content, '加载中...');
        try {
            const resp = await api.getConversations();
            const conversations = resp?.data?.conversations || [];
            AppState.set('conversations', conversations);
        } catch (e) {
            Toast.error('加载对话列表失败');
            this._render(AppState.get('conversations') || []);
        } finally {
            loader.close();
        }
    },

    _render(conversations) {
        if (!this.elements.list || !this.elements.empty) return;

        const list = Array.isArray(conversations) ? conversations : [];
        const currentId = AppState.get('currentConversationId');

        this.elements.list.innerHTML = '';

        if (list.length === 0) {
            this.elements.empty.classList.remove('hidden');
            this.elements.list.classList.add('hidden');
            this.elements.deleteAllBtn?.setAttribute('disabled', 'true');
            return;
        }

        this.elements.empty.classList.add('hidden');
        this.elements.list.classList.remove('hidden');
        this.elements.deleteAllBtn?.removeAttribute('disabled');

        list.forEach((conv) => {
            const item = this._createItem(conv, currentId);
            this.elements.list.appendChild(item);
        });
    },

    _createItem(conversation, currentId) {
        const item = document.createElement('div');
        item.className = 'history-item';
        item.dataset.conversationId = conversation.id;
        if (currentId && conversation.id === currentId) {
            item.classList.add('active');
        }

        const icon = document.createElement('div');
        icon.className = 'history-icon';
        icon.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M8.625 9.75a.375.375 0 11-.75 0 .375.375 0 01.75 0zm7.5 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zM21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M9.75 15.75h4.5" />
            </svg>
        `;

        const info = document.createElement('div');
        info.className = 'history-info';

        const title = document.createElement('div');
        title.className = 'history-title';
        title.textContent = conversation.title || '未命名对话';

        const meta = document.createElement('div');
        meta.className = 'history-meta';

        const count = Number.isFinite(conversation.message_count) ? conversation.message_count : (conversation.message_count || 0);
        const ts = conversation.updated_at || conversation.created_at || '';
        const timeText = typeof formatDate === 'function' && ts ? formatDate(ts, 'YYYY-MM-DD HH:mm') : (ts ? new Date(ts).toLocaleString() : '');
        meta.textContent = `${count} 条消息${timeText ? ` · ${timeText}` : ''}`;

        info.appendChild(title);
        info.appendChild(meta);

        const actions = document.createElement('div');
        actions.className = 'history-actions';

        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn btn-ghost btn-icon';
        deleteBtn.title = '删除';
        deleteBtn.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
            </svg>
        `;
        deleteBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            await this._deleteConversation(conversation);
        });

        actions.appendChild(deleteBtn);

        item.appendChild(icon);
        item.appendChild(info);
        item.appendChild(actions);

        item.addEventListener('click', () => {
            App?.loadConversation?.(conversation.id);
        });

        return item;
    },

    async _deleteConversation(conversation) {
        const ok = await ConfirmDialog.delete(conversation.title || '此对话');
        if (!ok) return;

        const loader = Loading.attach(this.elements.content, '删除中...');
        try {
            await api.deleteConversation(conversation.id);

            const currentId = AppState.get('currentConversationId');
            if (currentId && currentId === conversation.id) {
                App?.newChat?.();
            }

            const resp = await api.getConversations();
            const conversations = resp?.data?.conversations || [];
            AppState.set('conversations', conversations);
        } catch (e) {
            Toast.error('删除失败');
        } finally {
            loader.close();
        }
    }
};

// 导出（如果支持模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { HistoryModule };
}
