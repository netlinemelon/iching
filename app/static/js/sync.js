/**
 * IChingSync - 临时同步代码模块
 *
 * 通过 6 位短代码实现浏览器端数据与服务器的临时同步。
 * 数据上传后服务端保留 24 小时。
 *
 * API 通过 window.IChingSync 暴露。
 */
(function () {
    'use strict';

    function _log(msg) {
        if (window.console) {
            console.log('[IChingSync]', msg);
        }
    }

    function _warn(msg) {
        if (window.console) {
            console.warn('[IChingSync]', msg);
        }
    }

    window.IChingSync = {

        /**
         * 将当前 localStorage 中的历史数据上传到服务器，获取 6 位同步码。
         * @returns {Promise<{code: string, expires: string}>}
         */
        uploadForSync: function () {
            // 读取本地所有记录
            var allData = (function () {
                var records = [];
                try {
                    var raw = localStorage.getItem('iching_history');
                    if (raw) {
                        records = JSON.parse(raw);
                    }
                } catch (e) {
                    _warn('读取 localStorage 失败: ' + e.message);
                }
                return {
                    version: 1,
                    exported_at: new Date().toISOString(),
                    app: 'iching',
                    records: records,
                };
            })();

            _log('正在上传 ' + allData.records.length + ' 条记录...');

            return fetch('/api/sync/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(allData),
            }).then(function (res) {
                if (!res.ok) {
                    throw new Error('上传失败 (HTTP ' + res.status + ')');
                }
                return res.json();
            }).then(function (data) {
                _log('同步码已创建: ' + data.code);
                return {
                    code: data.code,
                    expires: data.expires_at,
                };
            });
        },

        /**
         * 通过同步码从服务器下载记录并合并到 localStorage。
         * 按 created_at + original_binary 去重。
         * @param {string} code - 6 位同步码
         * @returns {Promise<{imported: number}>}
         */
        downloadFromSync: function (code) {
            _log('正在通过同步码下载: ' + code);

            return fetch('/api/sync/' + encodeURIComponent(code), {
                method: 'GET',
            }).then(function (res) {
                if (!res.ok) {
                    if (res.status === 404) {
                        throw new Error('同步码无效或已过期');
                    }
                    throw new Error('下载失败 (HTTP ' + res.status + ')');
                }
                return res.json();
            }).then(function (data) {
                var remoteRecords = data.records || [];
                if (remoteRecords.length === 0) {
                    _log('同步码无数据');
                    return { imported: 0 };
                }

                // 读取现有本地记录
                var existing = [];
                try {
                    var stored = localStorage.getItem('iching_history');
                    if (stored) {
                        existing = JSON.parse(stored);
                    }
                } catch (e) {
                    _warn('读取 localStorage 失败: ' + e.message);
                }

                var imported = 0;
                remoteRecords.forEach(function (rec) {
                    // 按 created_at + original_binary 去重
                    var isDup = existing.some(function (r) {
                        return r.created_at === rec.created_at
                            && r.original_binary === rec.original_binary;
                    });
                    if (!isDup) {
                        // 确保有本地 ID
                        if (!rec.id) {
                            var ts = Date.now().toString(36);
                            var rand = Math.random().toString(36).substring(2, 8);
                            rec.id = 'local_' + ts + '_' + rand;
                        }
                        existing.push(rec);
                        imported++;
                    }
                });

                // 限制最多 200 条
                if (existing.length > 200) {
                    existing.sort(function (a, b) {
                        return (a.created_at || '').localeCompare(b.created_at || '');
                    });
                    existing.splice(0, existing.length - 200);
                }

                localStorage.setItem('iching_history', JSON.stringify(existing));
                _log('已合并 ' + imported + ' 条记录（来源: ' + code + '）');
                return { imported: imported };
            });
        },
    };

    _log('同步模块加载完成');
})();
