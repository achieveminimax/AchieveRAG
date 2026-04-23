/**
 * RAG 知识库助手 - UI 组件库
 * 
 * 提供通用的 UI 组件：Toast 提示、确认对话框、加载动画
 * 所有组件使用原生 DOM API 创建，无外部依赖
 */

// ==================== Toast 组件 ====================

/**
 * Toast 通知组件
 * 用于显示成功、错误、警告、信息提示
 */
class Toast {
    /**
     * 显示 Toast 提示
     * @param {string} message - 提示消息
     * @param {string} type - 提示类型: 'success' | 'error' | 'warning' | 'info'
     * @param {number} duration - 显示时长（毫秒），默认 3000
     */
    static show(message, type = 'info', duration = 3000) {
        const container = document.getElementById('toast-container');
        if (!container) {
            console.error('Toast container not found');
            return;
        }

        // 创建 Toast 元素
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        // 图标映射
        const icons = {
            success: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>`,
            error: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>`,
            warning: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>`,
            info: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
            </svg>`
        };

        toast.innerHTML = `
            <div class="toast-icon">${icons[type] || icons.info}</div>
            <div class="toast-message">${message}</div>
            <button class="toast-close" title="关闭">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
            </button>
        `;

        // 关闭按钮事件
        const closeBtn = toast.querySelector('.toast-close');
        closeBtn.addEventListener('click', () => {
            this._removeToast(toast);
        });

        // 添加到容器
        container.appendChild(toast);

        // 触发动画
        requestAnimationFrame(() => {
            toast.classList.add('show');
        });

        // 自动关闭
        if (duration > 0) {
            setTimeout(() => {
                this._removeToast(toast);
            }, duration);
        }

        return toast;
    }

    /**
     * 显示成功提示
     * @param {string} message - 提示消息
     * @param {number} duration - 显示时长
     */
    static success(message, duration = 3000) {
        return this.show(message, 'success', duration);
    }

    /**
     * 显示错误提示
     * @param {string} message - 提示消息
     * @param {number} duration - 显示时长
     */
    static error(message, duration = 5000) {
        return this.show(message, 'error', duration);
    }

    /**
     * 显示警告提示
     * @param {string} message - 提示消息
     * @param {number} duration - 显示时长
     */
    static warning(message, duration = 4000) {
        return this.show(message, 'warning', duration);
    }

    /**
     * 显示信息提示
     * @param {string} message - 提示消息
     * @param {number} duration - 显示时长
     */
    static info(message, duration = 3000) {
        return this.show(message, 'info', duration);
    }

    /**
     * 移除 Toast 元素
     * @private
     */
    static _removeToast(toast) {
        if (!toast || toast.classList.contains('hiding')) return;
        
        toast.classList.add('hiding');
        toast.classList.remove('show');
        
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }
}


// ==================== ConfirmDialog 组件 ====================

/**
 * 确认对话框组件
 * 用于需要用户确认的操作
 */
class ConfirmDialog {
    /**
     * 显示确认对话框
     * @param {Object} options - 配置选项
     * @param {string} options.title - 对话框标题
     * @param {string} options.message - 对话框消息
     * @param {string} options.confirmText - 确认按钮文本，默认"确认"
     * @param {string} options.cancelText - 取消按钮文本，默认"取消"
     * @param {string} options.type - 对话框类型: 'danger' | 'warning' | 'info'
     * @returns {Promise<boolean>} - 用户点击确认返回 true，取消返回 false
     */
    static show(options = {}) {
        const {
            title = '确认操作',
            message = '您确定要执行此操作吗？',
            confirmText = '确认',
            cancelText = '取消',
            type = 'warning'
        } = options;

        return new Promise((resolve) => {
            // 创建遮罩层
            const overlay = document.createElement('div');
            overlay.className = 'confirm-dialog-overlay';

            // 创建对话框
            const dialog = document.createElement('div');
            dialog.className = 'confirm-dialog';

            // 图标映射
            const icons = {
                danger: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                </svg>`,
                warning: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                </svg>`,
                info: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
                </svg>`
            };

            dialog.innerHTML = `
                <div class="confirm-dialog-icon confirm-dialog-icon-${type}">
                    ${icons[type] || icons.info}
                </div>
                <div class="confirm-dialog-content">
                    <h3 class="confirm-dialog-title">${title}</h3>
                    <p class="confirm-dialog-message">${message}</p>
                </div>
                <div class="confirm-dialog-actions">
                    <button class="btn btn-secondary confirm-dialog-cancel">${cancelText}</button>
                    <button class="btn btn-${type === 'danger' ? 'danger' : 'primary'} confirm-dialog-confirm">${confirmText}</button>
                </div>
            `;

            overlay.appendChild(dialog);
            document.body.appendChild(overlay);

            // 动画进入
            requestAnimationFrame(() => {
                overlay.classList.add('show');
                dialog.classList.add('show');
            });

            // 确认按钮
            const confirmBtn = dialog.querySelector('.confirm-dialog-confirm');
            const cancelBtn = dialog.querySelector('.confirm-dialog-cancel');

            const close = (result) => {
                overlay.classList.remove('show');
                dialog.classList.remove('show');
                
                setTimeout(() => {
                    if (overlay.parentNode) {
                        overlay.parentNode.removeChild(overlay);
                    }
                    resolve(result);
                }, 200);
            };

            confirmBtn.addEventListener('click', () => close(true));
            cancelBtn.addEventListener('click', () => close(false));

            // 点击遮罩关闭
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    close(false);
                }
            });

            // ESC 键关闭
            const handleKeydown = (e) => {
                if (e.key === 'Escape') {
                    close(false);
                    document.removeEventListener('keydown', handleKeydown);
                }
            };
            document.addEventListener('keydown', handleKeydown);
        });
    }

    /**
     * 显示删除确认对话框
     * @param {string} itemName - 要删除的项目名称
     * @returns {Promise<boolean>}
     */
    static delete(itemName = '此项') {
        return this.show({
            title: '确认删除',
            message: `您确定要删除"${itemName}"吗？此操作不可撤销。`,
            confirmText: '删除',
            cancelText: '取消',
            type: 'danger'
        });
    }
}


// ==================== Loading 组件 ====================

/**
 * 加载动画组件
 * 用于显示全局或局部加载状态
 */
class Loading {
    /**
     * 显示全局加载遮罩
     * @param {string} message - 加载提示文本
     * @returns {Object} - 控制器对象，包含 close 方法
     */
    static show(message = '加载中...') {
        // 检查是否已存在
        let overlay = document.getElementById('global-loading-overlay');
        
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'global-loading-overlay';
            overlay.className = 'loading-overlay';
            
            overlay.innerHTML = `
                <div class="loading-spinner">
                    <div class="spinner-ring"></div>
                    <div class="spinner-ring"></div>
                    <div class="spinner-ring"></div>
                </div>
                <div class="loading-message">${message}</div>
            `;
            
            document.body.appendChild(overlay);
        } else {
            const msgEl = overlay.querySelector('.loading-message');
            if (msgEl) msgEl.textContent = message;
        }

        // 显示动画
        requestAnimationFrame(() => {
            overlay.classList.add('show');
        });

        return {
            close: () => this.close(),
            updateMessage: (newMessage) => {
                const msgEl = overlay.querySelector('.loading-message');
                if (msgEl) msgEl.textContent = newMessage;
            }
        };
    }

    /**
     * 关闭全局加载遮罩
     */
    static close() {
        const overlay = document.getElementById('global-loading-overlay');
        if (overlay) {
            overlay.classList.remove('show');
            setTimeout(() => {
                if (overlay.parentNode) {
                    overlay.parentNode.removeChild(overlay);
                }
            }, 200);
        }
    }

    /**
     * 为指定元素添加局部加载状态
     * @param {HTMLElement} element - 目标元素
     * @param {string} message - 加载提示文本
     * @returns {Object} - 控制器对象
     */
    static attach(element, message = '') {
        if (!element) return { close: () => {} };

        // 添加相对定位
        const originalPosition = element.style.position;
        if (getComputedStyle(element).position === 'static') {
            element.style.position = 'relative';
        }

        // 创建局部加载层
        const loader = document.createElement('div');
        loader.className = 'loading-local';
        
        loader.innerHTML = `
            <div class="loading-spinner small">
                <div class="spinner-ring"></div>
                <div class="spinner-ring"></div>
                <div class="spinner-ring"></div>
            </div>
            ${message ? `<div class="loading-message">${message}</div>` : ''}
        `;

        element.appendChild(loader);

        requestAnimationFrame(() => {
            loader.classList.add('show');
        });

        return {
            close: () => {
                loader.classList.remove('show');
                setTimeout(() => {
                    if (loader.parentNode) {
                        loader.parentNode.removeChild(loader);
                    }
                    if (originalPosition) {
                        element.style.position = originalPosition;
                    } else {
                        element.style.position = '';
                    }
                }, 200);
            }
        };
    }

    /**
     * 显示按钮加载状态
     * @param {HTMLElement} button - 按钮元素
     * @param {string} loadingText - 加载时显示的文本
     * @returns {Object} - 控制器对象
     */
    static button(button, loadingText = '') {
        if (!button) return { close: () => {} };

        const originalContent = button.innerHTML;
        const originalDisabled = button.disabled;

        button.disabled = true;
        button.innerHTML = `
            <span class="btn-spinner"></span>
            ${loadingText || originalContent}
        `;
        button.classList.add('loading');

        return {
            close: () => {
                button.innerHTML = originalContent;
                button.disabled = originalDisabled;
                button.classList.remove('loading');
            }
        };
    }

    /**
     * 执行异步操作并显示加载状态
     * @param {Function} asyncFn - 异步函数
     * @param {string} message - 加载提示
     * @returns {Promise} - 异步操作结果
     */
    static async wrap(asyncFn, message = '加载中...') {
        const loader = this.show(message);
        try {
            const result = await asyncFn();
            return result;
        } finally {
            loader.close();
        }
    }
}


// ==================== 工具函数 ====================

/**
 * 防抖函数
 * @param {Function} fn - 要防抖的函数
 * @param {number} delay - 延迟时间（毫秒）
 * @returns {Function}
 */
function debounce(fn, delay = 300) {
    let timer = null;
    return function (...args) {
        if (timer) clearTimeout(timer);
        timer = setTimeout(() => {
            fn.apply(this, args);
        }, delay);
    };
}

/**
 * 节流函数
 * @param {Function} fn - 要节流的函数
 * @param {number} interval - 间隔时间（毫秒）
 * @returns {Function}
 */
function throttle(fn, interval = 300) {
    let lastTime = 0;
    return function (...args) {
        const now = Date.now();
        if (now - lastTime >= interval) {
            lastTime = now;
            fn.apply(this, args);
        }
    };
}

/**
 * 格式化日期时间
 * @param {string|Date} date - 日期对象或字符串
 * @param {string} format - 格式模板
 * @returns {string}
 */
function formatDate(date, format = 'YYYY-MM-DD HH:mm') {
    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    const seconds = String(d.getSeconds()).padStart(2, '0');

    return format
        .replace('YYYY', year)
        .replace('MM', month)
        .replace('DD', day)
        .replace('HH', hours)
        .replace('mm', minutes)
        .replace('ss', seconds);
}

/**
 * 格式化文件大小
 * @param {number} bytes - 字节数
 * @returns {string}
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const k = 1024;
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + units[i];
}

/**
 * 复制文本到剪贴板
 * @param {string} text - 要复制的文本
 * @returns {Promise<boolean>}
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        Toast.success('已复制到剪贴板');
        return true;
    } catch (err) {
        Toast.error('复制失败');
        return false;
    }
}


// 导出组件（如果支持模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { Toast, ConfirmDialog, Loading, debounce, throttle, formatDate, formatFileSize, copyToClipboard };
}
