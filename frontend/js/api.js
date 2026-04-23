/**
 * RAG 知识库助手 - API 客户端
 * 
 * 封装所有后端 API 调用，包括：
 * - 文件上传
 * - SSE 流式问答
 * - 对话管理
 * - 文档管理
 * - 系统设置
 */

/**
 * API 客户端类
 * 统一处理所有 HTTP 请求和错误处理
 */
class ApiClient {
    constructor() {
        // API 基础 URL
        const explicit =
            window.RAG_API_BASE_URL ||
            window.__RAG_APP_CONFIG__?.apiBaseURL ||
            localStorage.getItem('rag_api_base_url');

        if (explicit && typeof explicit === 'string') {
            this.baseURL = explicit.replace(/\/$/, '');
        } else {
            const port = window.location.port;
            const isDevFrontend =
                port === '3000' ||
                port === '3001' ||
                port === '8080';

            if (isDevFrontend) {
                this.baseURL = `${window.location.protocol}//127.0.0.1:8000/api`;
            } else {
                this.baseURL = `${window.location.origin}/api`;
            }
        }
        
        // 默认请求配置
        this.defaultConfig = {
            headers: {
                'Accept': 'application/json',
            }
        };
    }

    // ==================== 通用 HTTP 方法 ====================

    /**
     * 发送 GET 请求
     * @param {string} endpoint - API 端点
     * @returns {Promise<Object>}
     */
    async get(endpoint) {
        const url = `${this.baseURL}${endpoint}`;
        
        try {
            const response = await fetch(url, {
                method: 'GET',
                ...this.defaultConfig
            });
            
            return this._handleResponse(response);
        } catch (error) {
            return this._handleError(error);
        }
    }

    /**
     * 发送 POST 请求
     * @param {string} endpoint - API 端点
     * @param {Object|FormData} data - 请求数据
     * @returns {Promise<Object>}
     */
    async post(endpoint, data) {
        const url = `${this.baseURL}${endpoint}`;
        const isFormData = data instanceof FormData;
        
        const config = {
            method: 'POST',
            headers: {
                ...this.defaultConfig.headers,
                ...(isFormData ? {} : { 'Content-Type': 'application/json' })
            },
            body: isFormData ? data : JSON.stringify(data)
        };

        try {
            const response = await fetch(url, config);
            return this._handleResponse(response);
        } catch (error) {
            return this._handleError(error);
        }
    }

    /**
     * 发送 PUT 请求
     * @param {string} endpoint - API 端点
     * @param {Object} data - 请求数据
     * @returns {Promise<Object>}
     */
    async put(endpoint, data) {
        const url = `${this.baseURL}${endpoint}`;

        const config = {
            method: 'PUT',
            headers: {
                ...this.defaultConfig.headers,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        };

        try {
            const response = await fetch(url, config);
            return this._handleResponse(response);
        } catch (error) {
            return this._handleError(error);
        }
    }

    /**
     * 发送 DELETE 请求
     * @param {string} endpoint - API 端点
     * @returns {Promise<Object>}
     */
    async delete(endpoint) {
        const url = `${this.baseURL}${endpoint}`;
        
        try {
            const response = await fetch(url, {
                method: 'DELETE',
                ...this.defaultConfig
            });
            
            return this._handleResponse(response);
        } catch (error) {
            return this._handleError(error);
        }
    }

    /**
     * 处理响应
     * @private
     */
    async _handleResponse(response) {
        const data = await response.json().catch(() => null);
        
        if (!response.ok) {
            const errorMessage = data?.message || data?.detail || `请求失败: ${response.status}`;
            throw new Error(errorMessage);
        }
        
        return data;
    }

    /**
     * 处理错误
     * @private
     */
    _handleError(error) {
        console.error('API Error:', error);
        
        // 显示错误提示
        if (typeof Toast !== 'undefined') {
            Toast.error(error.message || '网络请求失败，请检查网络连接');
        }
        
        throw error;
    }

    // ==================== 文档管理 API ====================

    /**
     * 上传文档
     * @param {FileList|File[]} files - 文件列表
     * @param {Object} options - 选项
     * @param {boolean} options.showToast - 是否显示默认 Toast
     * @returns {Promise<Object>}
     */
    async uploadDocuments(files, options = {}) {
        const { showToast = true } = options;
        const formData = new FormData();
        
        for (const file of files) {
            formData.append('files', file);
        }

        try {
            const result = await this.post('/documents/upload', formData);
            if (showToast && typeof Toast !== 'undefined') {
                Toast.success('文档上传成功');
            }
            return result;
        } catch (error) {
            console.error('Upload failed:', error);
            throw error;
        }
    }

    /**
     * 获取文档列表
     * @returns {Promise<Object>}
     */
    async getDocuments() {
        return this.get('/documents');
    }

    /**
     * 获取文档预览内容
     * @param {string} id - 文档 ID
     * @returns {Promise<Object>}
     */
    async getDocumentContent(id) {
        return this.get(`/documents/${id}/content`);
    }

    /**
     * 删除文档
     * @param {string} id - 文档 ID
     * @returns {Promise<Object>}
     */
    async deleteDocument(id) {
        try {
            const result = await this.delete(`/documents/${id}`);
            Toast.success('文档已删除');
            return result;
        } catch (error) {
            console.error('Delete failed:', error);
            throw error;
        }
    }

    // ==================== 对话 API ====================

    /**
     * 获取对话列表
     * @returns {Promise<Object>}
     */
    async getConversations() {
        return this.get('/conversations');
    }

    /**
     * 获取单个对话详情
     * @param {string} id - 对话 ID
     * @returns {Promise<Object>}
     */
    async getConversation(id) {
        return this.get(`/conversations/${id}`);
    }

    /**
     * 创建新对话
     * @param {string} title - 对话标题（可选）
     * @returns {Promise<Object>}
     */
    async createConversation(title = null) {
        const data = title ? { title } : {};
        return this.post('/conversations', data);
    }

    /**
     * 删除对话
     * @param {string} id - 对话 ID
     * @returns {Promise<Object>}
     */
    async deleteConversation(id) {
        try {
            const result = await this.delete(`/conversations/${id}`);
            Toast.success('对话已删除');
            return result;
        } catch (error) {
            console.error('Delete conversation failed:', error);
            throw error;
        }
    }

    /**
     * 删除所有对话
     * @returns {Promise<Object>}
     */
    async deleteAllConversations() {
        try {
            const result = await this.delete('/conversations');
            Toast.success('已删除全部对话');
            return result;
        } catch (error) {
            console.error('Delete all conversations failed:', error);
            throw error;
        }
    }

    // ==================== SSE 流式问答 ====================

    /**
     * 流式问答
     * @param {string} question - 用户问题
     * @param {string|null} conversationId - 对话 ID
     * @param {Object} callbacks - 回调函数
     * @param {Function} callbacks.onToken - 收到 token 时回调
     * @param {Function} callbacks.onSources - 收到来源引用时回调
     * @param {Function} callbacks.onDone - 完成时回调
     * @param {Function} callbacks.onError - 错误时回调
     * @returns {Object} - 控制器对象，包含 abort 方法
     */
    chatStream(question, conversationId, callbacks = {}, options = {}) {
        const { onToken, onSources, onDone, onError } = callbacks;
        const { documentIds = [] } = options;
        
        // 创建 AbortController 用于取消请求
        const controller = new AbortController();
        
        const requestBody = {
            question,
            conversation_id: conversationId,
            document_ids: documentIds,
            stream: true
        };

        // 发起 fetch 请求
        fetch(`${this.baseURL}/chat/ask`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'text/event-stream'
            },
            body: JSON.stringify(requestBody),
            signal: controller.signal
        })
        .then(async (response) => {
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || `请求失败: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            // 读取流数据
            while (true) {
                const { done, value } = await reader.read();
                
                if (done) break;

                // 解码数据
                buffer += decoder.decode(value, { stream: true });
                
                // 处理 SSE 事件
                const events = this._parseSSEEvents(buffer);
                buffer = events.remainder;

                for (const event of events.parsed) {
                    this._handleSSEEvent(event, { onToken, onSources, onDone, onError });
                }
            }

            // 处理剩余数据
            if (buffer.trim()) {
                const events = this._parseSSEEvents(buffer + '\n\n');
                for (const event of events.parsed) {
                    this._handleSSEEvent(event, { onToken, onSources, onDone, onError });
                }
            }
        })
        .catch((error) => {
            if (error.name === 'AbortError') {
                console.log('Stream aborted');
                return;
            }
            
            console.error('Stream error:', error);
            if (onError) {
                onError(error);
            } else if (typeof Toast !== 'undefined') {
                Toast.error(error.message || '请求失败');
            }
        });

        return {
            abort: () => controller.abort()
        };
    }

    /**
     * 解析 SSE 事件
     * @private
     */
    _parseSSEEvents(buffer) {
        const normalized = buffer.replace(/\r/g, '');
        const parsed = [];
        let remainder = normalized;

        const parseEventBlock = (block) => {
            const evt = { event: 'message', data: null };
            const dataLines = [];
            const lines = block.split('\n');

            for (const line of lines) {
                if (!line) continue;
                if (line.startsWith(':')) continue;

                if (line.startsWith('event:')) {
                    evt.event = line.slice(6).trim() || evt.event;
                    continue;
                }

                if (line.startsWith('data:')) {
                    dataLines.push(line.slice(5).trimStart());
                    continue;
                }
            }

            if (dataLines.length > 0) {
                const dataStr = dataLines.join('\n');
                try {
                    evt.data = JSON.parse(dataStr);
                } catch {
                    evt.data = dataStr;
                }
            }

            return evt;
        };

        while (true) {
            const idx = remainder.indexOf('\n\n');
            if (idx === -1) break;
            const block = remainder.slice(0, idx);
            remainder = remainder.slice(idx + 2);

            if (!block.trim()) continue;
            parsed.push(parseEventBlock(block));
        }

        return { parsed, remainder };
    }

    /**
     * 处理 SSE 事件
     * @private
     */
    _handleSSEEvent(event, callbacks) {
        const { onToken, onSources, onDone, onError } = callbacks;

        switch (event.event) {
            case 'token':
                if (onToken && event.data?.content !== undefined) {
                    onToken(event.data.content);
                }
                break;

            case 'sources':
                if (onSources) {
                    const sources = Array.isArray(event.data) ? event.data : event.data?.sources;
                    if (sources) onSources(sources);
                }
                break;

            case 'done':
                if (onDone) {
                    onDone(event.data);
                }
                break;

            case 'error':
                console.error('SSE Error:', event.data);
                if (onError) {
                    onError(new Error(event.data?.message || '流式传输错误'));
                }
                break;

            default:
                console.warn('Unknown SSE event:', event);
        }
    }

    // ==================== 系统设置 API ====================

    /**
     * 获取系统设置
     * @returns {Promise<Object>}
     */
    async getSettings() {
        return this.get('/settings');
    }

    /**
     * 更新系统设置
     * @param {Object} settings - 设置项
     * @returns {Promise<Object>}
     */
    async updateSettings(settings) {
        try {
            const result = await this.put('/settings', settings);
            Toast.success('设置已保存');
            return result;
        } catch (error) {
            console.error('Update settings failed:', error);
            throw error;
        }
    }

    /**
     * 获取可用模型列表
     * @returns {Promise<Object>}
     */
    async getAvailableModels() {
        return this.get('/settings/models');
    }

    /**
     * 获取系统统计信息
     * @returns {Promise<Object>}
     */
    async getSystemStats() {
        return this.get('/settings/stats');
    }

    /**
     * 获取系统统计信息
     * @returns {Promise<Object>}
     */
    async getStats() {
        return this.get('/documents/stats');
    }
}


// ==================== 创建全局 API 客户端实例 ====================

const api = new ApiClient();


// 导出（如果支持模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ApiClient, api };
}
