/**
 * IChingStorage - 浏览器端 localStorage 数据持久化模块
 *
 * 将占卜结果存储在浏览器 localStorage 中，键名为 iching_history，
 * 存储为 JSON 数组。最多 200 条，超出时自动删除最旧记录。
 *
 * API 通过 window.IChingStorage 暴露。
 */
(function () {
    'use strict';

    if (window.IChingStorage) return;

    var STORAGE_KEY = 'iching_history';
    var MAX_ENTRIES = 200;

    /* ── 内部工具 ────────────────────────────────── */

    function _log(msg) {
        if (window.console) {
            console.log('[IChingStorage]', msg);
        }
    }

    function _warn(msg) {
        if (window.console) {
            console.warn('[IChingStorage]', msg);
        }
    }

    /** 生成本地唯一 ID：local_<base36-时间戳>_<随机6字符> */
    function _generateId() {
        var ts = Date.now().toString(36);
        var rand = Math.random().toString(36).substring(2, 8);
        return 'local_' + ts + '_' + rand;
    }

    /** 从 localStorage 读取全部记录（空数组兜底） */
    function _getAll() {
        try {
            var raw = localStorage.getItem(STORAGE_KEY);
            return raw ? JSON.parse(raw) : [];
        } catch (e) {
            _warn('读取 localStorage 失败: ' + e.message);
            return [];
        }
    }

    /** 将记录数组写回 localStorage */
    function _saveAll(records) {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(records));
        } catch (e) {
            _warn('写入 localStorage 失败: ' + e.message);
        }
    }

    /** 超过 MAX_ENTRIES 时按创建时间升序裁剪最旧记录 */
    function _enforceMax(records) {
        if (records.length > MAX_ENTRIES) {
            records.sort(function (a, b) {
                return (a.created_at || '').localeCompare(b.created_at || '');
            });
            var excess = records.length - MAX_ENTRIES;
            records.splice(0, excess);
            _log('已删除 ' + excess + ' 条最旧记录（上限 ' + MAX_ENTRIES + '）');
        }
        return records;
    }

    /* ── 公开 API ────────────────────────────────── */

    window.IChingStorage = {

        /**
         * 保存一条占卜结果到浏览器历史。
         * @param {Object} resultDict - 从服务器返回的完整占卜结果字典
         * @returns {string|null} 生成的本地 ID，重复时返回 null
         */
        saveResult: function (resultDict) {
            if (!resultDict) {
                _warn('saveResult: resultDict 为空');
                return null;
            }

            var records = _getAll();
            var id = _generateId();

            var entry = {
                id: id,
                created_at: resultDict.created_at || new Date().toISOString(),
                method: resultDict.method || '',

                original_binary: resultDict.original_binary || '',
                original_values: resultDict.original_values || [],
                original_hexagram: resultDict.original_hexagram || null,

                changed_hexagram: resultDict.changed_hexagram || null,
                changing_positions: resultDict.changing_positions || [],
                changing_count: resultDict.changing_count || 0,

                interpretation: resultDict.interpretation || null,
                mutual_hexagram: resultDict.mutual_hexagram || null,
                opposite_hexagram: resultDict.opposite_hexagram || null,
                reverse_hexagram: resultDict.reverse_hexagram || null,
                body_use: resultDict.body_use || null,

                lines: resultDict.lines || [],
                toss_details: resultDict.toss_details || null,

                question: resultDict.question || '',
                ai_interpretation: resultDict.ai_interpretation || '',

                is_favorite: !!resultDict.is_favorite,
                share_token: resultDict.share_token || '',
            };

            // 按 created_at + original_binary 去重（避免页面刷新重复保存）
            var isDuplicate = records.some(function (r) {
                return r.created_at === entry.created_at
                    && r.original_binary === entry.original_binary;
            });
            if (isDuplicate) {
                _log('跳过重复记录（相同 created_at + binary）');
                return null;
            }

            records.push(entry);
            _enforceMax(records);

            try {
                _saveAll(records);
                _log('已保存记录: ' + id);
                return id;
            } catch (e) {
                // localStorage 配额不足时删除最旧记录重试
                if (e.name === 'QuotaExceededError' || e.code === 22 || e.code === 1014) {
                    _warn('localStorage 配额满，删除最旧记录后重试...');
                    records.sort(function (a, b) {
                        return (a.created_at || '').localeCompare(b.created_at || '');
                    });
                    records.shift();
                    try {
                        _saveAll(records);
                        return id;
                    } catch (e2) {
                        _warn('清理后仍无法写入 localStorage');
                        return null;
                    }
                }
                _warn('保存失败: ' + e.message);
                return null;
            }
        },

        /**
         * 获取历史记录列表（按创建时间倒序）。
         * @param {number} [page=1]
         * @param {number} [perPage=20]
         * @returns {{total: number, results: Array, page: number, totalPages: number}}
         */
        getHistory: function (page, perPage) {
            page = page || 1;
            perPage = perPage || 20;
            var records = _getAll();

            // 按创建时间倒序（最新的在前）
            records.sort(function (a, b) {
                return (b.created_at || '').localeCompare(a.created_at || '');
            });

            var total = records.length;
            var totalPages = Math.max(1, Math.ceil(total / perPage));
            var start = (page - 1) * perPage;
            var end = Math.min(start + perPage, total);

            return {
                total: total,
                results: records.slice(start, end),
                page: page,
                totalPages: totalPages,
            };
        },

        /**
         * 按本地 ID 获取单条记录。
         * @param {string} id
         * @returns {Object|null}
         */
        getResult: function (id) {
            var records = _getAll();
            for (var i = 0; i < records.length; i++) {
                if (records[i].id === id) {
                    return records[i];
                }
            }
            return null;
        },

        /**
         * 切换收藏状态。
         * @param {string} id
         * @returns {boolean} 切换后的收藏状态
         */
        toggleFavorite: function (id) {
            var records = _getAll();
            for (var i = 0; i < records.length; i++) {
                if (records[i].id === id) {
                    records[i].is_favorite = !records[i].is_favorite;
                    _saveAll(records);
                    _log('切换收藏: ' + id + ' -> ' + records[i].is_favorite);
                    return records[i].is_favorite;
                }
            }
            _warn('toggleFavorite: 未找到记录 ' + id);
            return false;
        },

        /**
         * 删除一条记录。
         * @param {string} id
         */
        deleteResult: function (id) {
            var records = _getAll();
            var filtered = records.filter(function (r) {
                return r.id !== id;
            });
            if (filtered.length !== records.length) {
                _saveAll(filtered);
                _log('已删除记录: ' + id);
            } else {
                _warn('deleteResult: 未找到记录 ' + id);
            }
        },

        /**
         * 导出全部历史为 JSON 文件下载。
         * @param {string} [filename='iching_history.json']
         */
        exportJSON: function (filename) {
            filename = filename || 'iching_history.json';
            var records = _getAll();
            var exportData = {
                version: 1,
                exported_at: new Date().toISOString(),
                app: 'iching',
                records: records,
            };
            var blob = new Blob([JSON.stringify(exportData, null, 2)], {
                type: 'application/json',
            });
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            _log('已导出 ' + records.length + ' 条记录');
        },

        /**
         * 从 JSON 文件导入历史记录（与 exportJSON 格式兼容，完整 round-trip）。
         * @param {File} file
         * @returns {Promise<{imported: number, errors: number}>}
         */
        importJSON: function (file) {
            return new Promise(function (resolve, reject) {
                var reader = new FileReader();
                reader.onload = function (e) {
                    try {
                        var data = JSON.parse(e.target.result);

                        // 验证格式
                        if (!data.records || !Array.isArray(data.records)) {
                            reject(new Error('无效格式：缺少 records 数组'));
                            return;
                        }

                        var records = _getAll();
                        var imported = 0;
                        var errors = 0;

                        data.records.forEach(function (rec) {
                            // 确保每条记录都有 ID
                            if (!rec.id) {
                                var ts = Date.now().toString(36);
                                var rand = Math.random().toString(36).substring(2, 8);
                                rec.id = 'local_' + ts + '_' + rand;
                            }

                            // 按 created_at + original_binary 去重
                            var isDup = records.some(function (r) {
                                return r.created_at === rec.created_at
                                    && r.original_binary === rec.original_binary;
                            });
                            if (isDup) {
                                errors++;
                                return;
                            }

                            records.push(rec);
                            imported++;
                        });

                        _enforceMax(records);
                        _saveAll(records);
                        _log('导入完成：' + imported + ' 条成功，' + errors + ' 条重复');
                        resolve({ imported: imported, errors: errors });
                    } catch (err) {
                        reject(err);
                    }
                };
                reader.onerror = function () {
                    reject(new Error('读取文件失败'));
                };
                reader.onabort = function () {
                    reject(new Error('读取已取消'));
                };
                reader.readAsText(file);
            });
        },

        /**
         * 获取存储统计信息。
         * @returns {{total: number, oldest: string|null, newest: string|null, size: number}}
         */
        getStats: function () {
            var records = _getAll();
            var total = records.length;
            var oldest = null;
            var newest = null;

            if (total > 0) {
                var sorted = records.slice().sort(function (a, b) {
                    return (a.created_at || '').localeCompare(b.created_at || '');
                });
                oldest = sorted[0].created_at;
                newest = sorted[sorted.length - 1].created_at;
            }

            var size = 0;
            try {
                size = new Blob([JSON.stringify(records)]).size;
            } catch (e) {
                size = JSON.stringify(records).length;
            }

            return {
                total: total,
                oldest: oldest,
                newest: newest,
                size: size,
            };
        },

        /**
         * 检查 localStorage 是否可用。
         * @returns {boolean}
         */
        isAvailable: function () {
            try {
                var testKey = '__iching_test__';
                localStorage.setItem(testKey, '1');
                localStorage.removeItem(testKey);
                return true;
            } catch (e) {
                return false;
            }
        },

        /**
         * 保存或更新 AI 解卦结果到已有记录。
         * 通过 share_token 匹配记录并更新 ai_interpretation 字段。
         * @param {string} shareToken
         * @param {string} text - AI 解读文本
         * @returns {boolean} 是否成功更新
         */
        saveAIInterpretation: function (shareToken, text) {
            if (!shareToken || !text) {
                _warn('saveAIInterpretation: 参数不完整');
                return false;
            }
            var records = _getAll();
            for (var i = 0; i < records.length; i++) {
                if (records[i].share_token === shareToken) {
                    records[i].ai_interpretation = text;
                    _saveAll(records);
                    _log('已更新 AI 解卦结果: ' + shareToken);
                    return true;
                }
            }
            _warn('saveAIInterpretation: 未找到匹配的记录 ' + shareToken);
            return false;
        },

        /**
         * 清除所有本地存储的占卜数据。
         */
        clearAll: function () {
            localStorage.removeItem(STORAGE_KEY);
            _log('已清除所有本地数据');
        },
    };

    _log('存储模块加载完成');
})();

/* IChingSync 由 sync.js 独立提供 */
