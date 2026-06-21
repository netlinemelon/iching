/**
 * AI 智能解卦 — AI-Powered I Ching Interpretation
 *
 * Alpine.js 组件，用于请求 AI 对占卜结果进行综合解读。
 */
(function () {
  'use strict';

  document.addEventListener('alpine:init', function () {
    Alpine.data('aiInterpret', function () {
      return {
        state: 'idle', // idle | loading | done | error
        errorMsg: '',
        result: '',

        rendered: '',

        async requestAI() {
          this.state = 'loading';
          this.errorMsg = '';

          // 从 URL 获取 token
          var urlParams = new URLSearchParams(window.location.search);
          var token = urlParams.get('token');
          if (!token) {
            this.state = 'error';
            this.errorMsg = '未找到占卜令牌，请重新起卦。';
            return;
          }

          try {
            var resp = await fetch('/api/interpret/' + encodeURIComponent(token), {
              method: 'POST',
              headers: { 'Accept': 'application/json' },
            });

            if (!resp.ok) {
              var errText = await resp.text();
              throw new Error(errText || 'AI 解卦服务暂不可用');
            }

            var data = await resp.json();
            this.result = data.interpretation;

            // 将 Markdown 转为简单 HTML
            this.rendered = this._renderMarkdown(data.interpretation);
            this.state = 'done';
          } catch (err) {
            this.state = 'error';
            this.errorMsg = err.message || '请求失败，请检查网络连接后重试。';
          }
        },

        /** 简易 Markdown → HTML */
        _renderMarkdown: function (md) {
          if (!md) return '';
          var html = md
            // 转义 HTML
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            // 标题
            .replace(/^### (.+)$/gm, '<h5>$1</h5>')
            .replace(/^## (.+)$/gm, '<h4>$1</h4>')
            .replace(/^# (.+)$/gm, '<h3>$1</h3>')
            // 粗体
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            // 列表
            .replace(/^- (.+)$/gm, '<li>$1</li>')
            .replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
            // 段落
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>');

          return '<p>' + html + '</p>';
        }
      };
    });
  });
})();
