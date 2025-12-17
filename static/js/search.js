class SearchApp {
    constructor() {
        this.searchKeyword = '';
        this.selectedType = 'quark';
        this.searchResults = [];
        this.currentPage = 1;
        this.pageSize = 10;
        this.totalPages = 1;
        this.isChecking = false;

        this.initElements();
        this.bindEvents();
    }

    initElements() {
        this.searchInput = document.getElementById('searchInput');
        this.cloudType = document.getElementById('cloudType');
        this.searchBtn = document.getElementById('searchBtn');
        this.resultsContainer = document.getElementById('resultsContainer');
        this.pagination = document.getElementById('pagination');
    }
    showLoadingModal() {
    // 创建等待弹窗元素
    const loadingModal = document.createElement('div');
    loadingModal.className = 'loading-modal';
    loadingModal.innerHTML = `        <div class="loading-modal-content">
            <div class="spinner"></div>
<!--            <p>正在获取分享链接...</p>-->
        </div>
    `;

    // 添加到页面
    document.body.appendChild(loadingModal);
    return loadingModal;
}
    bindEvents() {
        this.searchBtn.addEventListener('click', () => this.performSearch());
        this.searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.performSearch();
            }
        });
        this.cloudType.addEventListener('change', (e) => {
            this.selectedType = e.target.value;
        });
    }

    // 在 SearchApp 类中添加隐藏等待弹窗的方法
    hideLoadingModal(loadingModal) {
        if (loadingModal && loadingModal.parentNode) {
            loadingModal.parentNode.removeChild(loadingModal);
        }
    }
    // 修改 performSearch 方法中的数据处理部分
    async performSearch() {
        this.searchKeyword = this.searchInput.value.trim();
        if (!this.searchKeyword) {
            alert('请输入搜索关键词');
            return;
        }

        try {
            // 显示加载状态
            this.resultsContainer.innerHTML = '<p>搜索中...</p>';

            const response = await fetch('/get_resource', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                    },
                body: JSON.stringify({
                    kw: this.searchKeyword,
                    cloud_types: [this.selectedType]
                })
            });

            const data = await response.json();

            if (data && data.data && data.data.merged_by_type) {
                // 根据选择的类型获取对应结果
                let results = data.data.merged_by_type[this.selectedType] || [];

                // 按 datetime 字段排序，最新日期优先
                results.sort((a, b) => {
                    const dateA = new Date(a.datetime || 0);
                    const dateB = new Date(b.datetime || 0);
                    return dateB - dateA; // 降序排列，最新的在前面
                });
                // 确保初始结果不包含有效性状态
                results = results.map(item => {
                    // 移除可能存在的 valid 属性，或设置为 undefined
                    const cleanItem = { ...item };
                    delete cleanItem.valid;
                    return cleanItem;
                });
                // 显示检测中状态
                this.resultsContainer.innerHTML = '<p>正在检测链接有效性...</p>';

                // 批量检测链接有效性
                this.searchResults = results;
                this.totalPages = Math.ceil(this.searchResults.length / this.pageSize);
                this.currentPage = 1;
                this.renderResults();
                this.renderPagination();
            } else {
                this.resultsContainer.innerHTML = '<p>未找到相关结果</p>';
                this.pagination.innerHTML = '';
            }
        } catch (error) {
            console.error('搜索出错:', error);
            this.resultsContainer.innerHTML = '<p>搜索失败，请稍后重试</p>';
            this.pagination.innerHTML = '';
        }
    }

    // renderResults() {
    //     const startIndex = (this.currentPage - 1) * this.pageSize;
    //     const endIndex = startIndex + this.pageSize;
    //     const pageResults = this.searchResults.slice(startIndex, endIndex);
    //
    //     if (pageResults.length === 0) {
    //         this.resultsContainer.innerHTML = '<p>当前页无数据</p>';
    //         return;
    //     }
    //
    //     let html = '';
    //     pageResults.forEach((item, index) => {
    //         // 处理 datetime 显示
    //         let datetimeDisplay = '';
    //         if (item.datetime && item.datetime !== '0001-01-01T00:00:00Z') {
    //             try {
    //                 const date = new Date(item.datetime);
    //                 // 格式化日期显示
    //                 datetimeDisplay = `
    //                     <div class="result-datetime">
    //                         更新时间: ${date.toLocaleDateString('zh-CN')}
    //                     </div>
    //                 `;
    //             } catch (e) {
    //                 // 日期解析失败时不显示
    //             }
    //         }
    //
    //         // 处理 images 显示
    //         let imageDisplay = '';
    //         if (item.images) {
    //             let imageUrl = '';
    //             // 处理不同格式的 images 数据
    //             if (Array.isArray(item.images)) {
    //                 imageUrl = item.images[0] || '';
    //             } else if (typeof item.images === 'string') {
    //                 // 尝试解析字符串格式的图片数组
    //                 try {
    //                     const parsedImages = JSON.parse(item.images.replace(/'/g, '"'));
    //                     if (Array.isArray(parsedImages)) {
    //                         imageUrl = parsedImages[0] || '';
    //                     } else {
    //                         imageUrl = item.images;
    //                     }
    //                 } catch (e) {
    //                     imageUrl = item.images;
    //                 }
    //             }
    //
    //             if (imageUrl) {
    //                 imageDisplay = `
    //                     <div class="result-image">
    //                         <img src="${imageUrl}" alt="${item.note || '图片'}" onerror="this.style.display='none'">
    //                     </div>
    //                 `;
    //             }
    //         }
    //
    //         // 根据有效性状态设置样式
    //         // 根据有效性状态设置样式 (更严格的判断)
    //         let validityClass = '';
    //         let getLinkDisabled = '';
    //
    //         // 只有在明确检查过且无效时才置灰
    //         if (item.hasOwnProperty('valid') && item.valid === false) {
    //             validityClass = 'invalid-result';
    //             getLinkDisabled = 'disabled';
    //         }
    //         html += `
    //             <div class="result-item ${validityClass}">
    //                 ${imageDisplay}
    //                 <div class="result-info">
    //                     <span class="result-name">${item.note || '未知名称'}</span>
    //                     ${datetimeDisplay}
    //                 </div>
    //                 <button class="get-link-btn" data-index="${startIndex + index}" ${getLinkDisabled}>
    //                     获取链接
    //                 </button>
    //             </div>
    //         `;
    //     });
    //
    //     // 添加检查有效性按钮
    //     html += `
    //         <div class="check-validity-container">
    //             <button class="check-validity-btn" id="checkValidityBtn">
    //                 检查当前页链接有效性
    //             </button>
    //         </div>
    //     `;
    //
    //     this.resultsContainer.innerHTML = html;
    //
    //     // 绑定获取链接按钮事件
    //     document.querySelectorAll('.get-link-btn').forEach(btn => {
    //         btn.addEventListener('click', (e) => {
    //             if (!e.target.disabled) {
    //                 const index = parseInt(e.target.dataset.index);
    //                 this.getShareLink(this.searchResults[index]);
    //             }
    //         });
    //     });
    //
    //     // 绑定检查有效性按钮事件
    //     const checkBtn = document.getElementById('checkValidityBtn');
    //     if (checkBtn) {
    //         checkBtn.addEventListener('click', () => {
    //             this.checkCurrentPageValidity();
    //         });
    //     }
    // }


    renderResults() {
        const startIndex = (this.currentPage - 1) * this.pageSize;
        const endIndex = startIndex + this.pageSize;
        const pageResults = this.searchResults.slice(startIndex, endIndex);

        if (pageResults.length === 0) {
            this.resultsContainer.innerHTML = '<p>当前页无数据</p>';
            return;
        }

        // 先添加检查有效性按钮（放在顶部）
        let html = "";

        // 然后添加搜索结果
        pageResults.forEach((item, index) => {
            // 处理 datetime 显示
            let datetimeDisplay = '';
            if (item.datetime && item.datetime !== '0001-01-01T00:00:00Z') {
                try {
                    const date = new Date(item.datetime);
                    // 格式化日期显示
                    datetimeDisplay = `
                        <div class="result-datetime">
                            更新时间: ${date.toLocaleDateString('zh-CN')}
                        </div>
                    `;
                } catch (e) {
                    // 日期解析失败时不显示
                }
            }

            // 处理 images 显示
            let imageDisplay = '';
            if (item.images) {
                let imageUrl = '';
                // 处理不同格式的 images 数据
                if (Array.isArray(item.images)) {
                    imageUrl = item.images[0] || '';
                } else if (typeof item.images === 'string') {
                    // 尝试解析字符串格式的图片数组
                    try {
                        const parsedImages = JSON.parse(item.images.replace(/'/g, '"'));
                        if (Array.isArray(parsedImages)) {
                            imageUrl = parsedImages[0] || '';
                        } else {
                            imageUrl = item.images;
                        }
                    } catch (e) {
                        imageUrl = item.images;
                    }
                }

                if (imageUrl) {
                    imageDisplay = `
                        <div class="result-image">
                            <img src="${imageUrl}" alt="${item.note || '图片'}" onerror="this.style.display='none'">
                        </div>
                    `;
                }
            }

            // 根据有效性状态设置样式
            let validityClass = '';
            let getLinkDisabled = '';

            // 只有在明确检查过且无效时才置灰
            if (item.hasOwnProperty('valid') && item.valid === false) {
                validityClass = 'invalid-result';
                getLinkDisabled = 'disabled';
            }

            html += `<div class="result-item ${validityClass}">
                ${imageDisplay}                <div class="result-info">
                    <span class="result-name">${item.note || '未知名称'}</span>
                    ${datetimeDisplay}                </div>
                <button class="get-link-btn" data-index="${startIndex + index}" ${getLinkDisabled}>
                    获取链接
                </button>
            </div>
        `;
        });

        this.resultsContainer.innerHTML = html;

        // 绑定获取链接按钮事件
        document.querySelectorAll('.get-link-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                if (!e.target.disabled) {
                    const index = parseInt(e.target.dataset.index);
                    this.getShareLink(this.searchResults[index]);
                }
            });
        });

        // 绑定检查有效性按钮事件
        const checkBtn = document.getElementById('checkValidityBtn');
        if (checkBtn) {
            checkBtn.addEventListener('click', () => {
                this.checkCurrentPageValidity();
            });
        }
    }


    async getShareLink(item) {
    // 显示等待弹窗
    const loadingModal = this.showLoadingModal();

    try {
        const response = await fetch('/get_share', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                share_type: this.selectedType,
                share_name: item.note,
                share_url: item.url,
                share_password: item.password || ''
            })
        });

        // 隐藏等待弹窗
        this.hideLoadingModal(loadingModal);

        const data = await response.json();

        if (data && data.message) {
            // 显示分享链接在模态框中
            this.showModal(`分享链接: ${data.message}`);
        } else {
            this.showModal('获取分享链接失败');
        }
    } catch (error) {
        console.error('获取分享链接出错:', error);
        // 隐藏等待弹窗
        this.hideLoadingModal(loadingModal);
        this.showModal('获取分享链接失败，请稍后重试');
    }
}

    showModal(message) {
    // 创建模态框元素
    const modal = document.createElement('div');
    modal.className = 'modal';

    // 提取分享链接用于复制功能
    let displayMessage = message;
    let shareLink = '';

    if (message.includes('分享链接:')) {
        const parts = message.split('分享链接:');
        displayMessage = `分享链接: ${parts[1].trim()}`;
        shareLink = parts[1].trim();
    }
    // 添加时效性提示
    const expiryWarning = '<div class="expiry-warning">⚠️ 链接时效3分钟，过期请重新获取</div>';

    modal.innerHTML = `
        <div class="modal-content">
            <span class="close">&times;</span>
            <p>${displayMessage}</p>
            ${expiryWarning}
            <div class="modal-buttons">
                <button class="copy-btn" data-link="${shareLink}">复制链接</button>
                <button class="modal-close-btn">确定</button>
            </div>
        </div>
    `;

    // 添加到页面
    document.body.appendChild(modal);

    // 绑定关闭事件
    const closeElements = modal.querySelectorAll('.close, .modal-close-btn');
    closeElements.forEach(element => {
        element.addEventListener('click', () => {
            document.body.removeChild(modal);
        });
    });

    // 绑定复制按钮事件
    const copyBtn = modal.querySelector('.copy-btn');
    if (copyBtn) {
    copyBtn.addEventListener('click', (e) => {
        const link = e.target.dataset.link;
        this.copyToClipboard(link);
        // 修改为显示对钩而不是弹窗
        e.target.textContent = '✓ 已复制';
        e.target.style.backgroundColor = '#28a745';
        setTimeout(() => {
            e.target.textContent = '复制链接';
            e.target.style.backgroundColor = '';
        }, 2000);
    });
}

    // 点击模态框外部关闭
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            document.body.removeChild(modal);
        }
    });
}

    copyToClipboard(text) {
        // 创建临时文本区域
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-9999px';
        document.body.appendChild(textArea);

        // 选择并复制文本
        textArea.select();
        try {
            const successful = document.execCommand('copy');
            // 移除所有 alert 弹窗，仅在控制台输出日志
            if (successful) {
                console.log('链接已复制到剪贴板');
            } else {
                console.log('复制失败，请手动复制');
            }
        } catch (err) {
            // 兼容性处理，移除 alert 弹窗
            console.error('复制失败:', err);
            console.log('复制失败，请手动复制');
        }

        // 移除临时元素
        document.body.removeChild(textArea);
    }


    renderPagination() {
        if (this.totalPages <= 1) {
            this.pagination.innerHTML = '';
            return;
        }

        let html = `
            <button class="page-btn" id="prevBtn" ${this.currentPage === 1 ? 'disabled' : ''}>
                上一页
            </button>
            <span class="page-info">
                第 ${this.currentPage} 页，共 ${this.totalPages} 页
            </span>
            <button class="page-btn" id="nextBtn" ${this.currentPage === this.totalPages ? 'disabled' : ''}>
                下一页
            </button>
        `;

        this.pagination.innerHTML = html;

        // 绑定分页按钮事件
        document.getElementById('prevBtn')?.addEventListener('click', () => {
            if (this.currentPage > 1) {
                this.currentPage--;
                this.renderResults();
                this.renderPagination();
            }
        });

        document.getElementById('nextBtn')?.addEventListener('click', () => {
            if (this.currentPage < this.totalPages) {
                this.currentPage++;
                this.renderResults();
                this.renderPagination();
            }
        });
    }

    // 添加检查链接有效性的方法
    async checkCurrentPageValidity() {
        // 防止重复点击
        if (this.isChecking) {
            return;
        }

        this.isChecking = true;

        // 显示等待弹窗
        const loadingModal = this.showLoadingModal();

        try {
            // 获取当前页面的结果
            const startIndex = (this.currentPage - 1) * this.pageSize;
            const endIndex = startIndex + this.pageSize;
            const pageResults = this.searchResults.slice(startIndex, endIndex);

            // 创建检查任务数组
            const checkPromises = pageResults.map(async (item, index) => {
                try {
                    const response = await fetch('/check_valid', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                    body: JSON.stringify({
                            url: item.url,
                            share_type: this.selectedType
                        })
                    });

                    const data = await response.json();
                    // 确保 valid 是布尔值
                    const isValid = data && data === true;

                    return {
                        index: startIndex + index,
                        valid: isValid
                    };
                } catch (error) {
                    console.error('检查链接有效性出错:', error);
                    return {
                        index: startIndex + index,
                        valid: false
                    };
                }
            });

            // 等待所有检查完成
            const results = await Promise.all(checkPromises);

            // 更新搜索结果的有效性状态
            results.forEach(result => {
                if (this.searchResults[result.index]) {
                    this.searchResults[result.index].valid = result.valid;
                }
            });

            // 重新渲染当前页面
            this.renderResults();

            // 显示检查完成提示
            alert(`检查完成！共检查${pageResults.length}个链接`);

        } catch (error) {
            console.error('检查链接有效性出错:', error);
            alert('检查失败，请稍后重试');
        } finally {
            // 确保总是隐藏等待弹窗并重置状态
            this.hideLoadingModal(loadingModal);
            this.isChecking = false;
        }
    }

}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    new SearchApp();
});
