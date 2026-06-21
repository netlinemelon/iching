/**
 * 卦象渲染 — Hexagram SVG Rendering
 *
 * 绘制六爻卦的 SVG：
 * - 阳爻：实心矩形（金色）
 * - 阴爻：两个分离的矩形（灰色）
 * - 变爻：红色标记
 * - 爻位标签
 */

(function () {
  'use strict';

  var HexagramRenderer = {
    /**
     * 默认配置
     */
    defaults: {
      width: 200,
      height: 220,
      lineHeight: 14,
      lineGap: 8,
      lineWidth: 80,
      yinGap: 10,
      labelWidth: 40,
      padding: 10,
      colorYang: '#C9A96E',
      colorYin: '#4A4A4A',
      colorChanging: '#8B0000',
      colorText: '#5A5A6E',
      colorTextDark: '#1A1A2E',
      animate: false
    },

    /**
     * 获取爻的二进制值（从 lines 数组，index 0 = 初爻）
     */
    getBinaryFromLines: function (lines) {
      // lines: 从下到上 [{is_yang: bool, changing: bool}, ...]
      var binary = '';
      for (var i = lines.length - 1; i >= 0; i--) {
        binary += lines[i].is_yang ? '1' : '0';
      }
      return binary;
    },

    /**
     * 将六爻数据渲染为 SVG 字符串
     *
     * @param {Array} lines - 六爻数组，从下到上 (position 1-6),
     *                        每项: { is_yang, changing, name }
     * @param {Object} opts - 可选配置
     * @returns {string} SVG 字符串
     */
    render: function (lines, opts) {
      opts = Object.assign({}, this.defaults, opts || {});

      if (!lines || lines.length !== 6) {
        return '<svg></svg>';
      }

      var W = opts.width;
      var H = opts.height;
      var lineH = opts.lineHeight;
      var gap = opts.lineGap;
      var lw = opts.lineWidth;
      var yinGap = opts.yinGap;
      var labelW = opts.labelWidth;
      var pad = opts.padding;

      // 绘制区域
      var drawW = W - pad * 2;
      var drawH = 6 * lineH + 5 * gap;
      var startY = pad + (H - pad * 2 - drawH) / 2;
      var centerX = pad + labelW + (drawW - labelW) / 2;
      var lineTotalW = drawW - labelW - pad;
      var lineSegmentW = (lineTotalW - yinGap) / 2;

      var svg = '<svg class="hexagram-svg" xmlns="http://www.w3.org/2000/svg" ' +
                'viewBox="0 0 ' + W + ' ' + H + '" width="' + W + '" height="' + H + '">';

      // 背景
      svg += '<rect width="' + W + '" height="' + H + '" fill="none"/>';

      // 从下到上绘制 (position 1 = 底部)
      for (var i = 0; i < 6; i++) {
        var line = lines[i];
        var y = startY + (6 - 1 - i) * (lineH + gap); // 从顶部开始画

        var isYang = line.is_yang;
        var isChanging = line.changing;
        var lineClass = isYang ? 'yang-line' : 'yin-line';
        var color = isYang ? opts.colorYang : opts.colorYin;
        if (isChanging) color = opts.colorChanging;

        if (isYang) {
          // 阳爻：完整矩形
          var x = centerX - lw / 2;
          svg += '<rect class="hexagram-line yang-line' +
                 (isChanging ? ' changing-line' : '') + '" ' +
                 'x="' + x + '" y="' + y + '" width="' + lw + '" height="' + lineH + '" ' +
                 'rx="3" ry="3" fill="' + color + '" ' +
                 (isChanging ? 'stroke="' + opts.colorChanging + '" stroke-width="1.5"' : '') + '/>';
        } else {
          // 阴爻：两个分离矩形
          var x1 = centerX - lw / 2;
          svg += '<rect class="hexagram-line yin-line-left' +
                 (isChanging ? ' changing-line' : '') + '" ' +
                 'x="' + x1 + '" y="' + y + '" width="' + lineSegmentW + '" height="' + lineH + '" ' +
                 'rx="3" ry="3" fill="' + color + '"/>';
          var x2 = centerX + lw / 2 - lineSegmentW;
          svg += '<rect class="hexagram-line yin-line-right' +
                 (isChanging ? ' changing-line' : '') + '" ' +
                 'x="' + x2 + '" y="' + y + '" width="' + lineSegmentW + '" height="' + lineH + '" ' +
                 'rx="3" ry="3" fill="' + color + '"/>';
        }

        // 变爻标记
        if (isChanging) {
          var markerX = centerX + lw / 2 + 8;
          var markerY = y + lineH / 2;
          svg += '<text class="changing-marker" x="' + markerX + '" y="' + markerY + '" ' +
                 'fill="' + opts.colorChanging + '" font-size="12" font-weight="bold" ' +
                 'dominant-baseline="middle">×</text>';  // ×
        }

        // 爻位标签（左侧）
        var label = line.name || '';
        var labelX = pad + labelW - 4;
        svg += '<text class="line-label" x="' + labelX + '" y="' + (y + lineH / 2) + '" ' +
               'fill="' + opts.colorText + '" font-size="11" font-family="Microsoft YaHei, sans-serif" ' +
               'text-anchor="end" dominant-baseline="middle">' + this._escapeXml(label) + '</text>';
      }

      // 底部卦名
      if (opts.name) {
        svg += '<text class="hexagram-svg-name" x="' + (W / 2) + '" y="' + (H - 4) + '" ' +
               'font-size="13" font-family="Microsoft YaHei, sans-serif" fill="' + opts.colorTextDark + '" ' +
               'text-anchor="end" dominant-baseline="auto">' +
               this._escapeXml(opts.name) + '</text>';
      }
      if (opts.unicode) {
        svg += '<text class="hexagram-svg-unicode" x="' + (W / 2) + '" y="' + (H - 4) + '" ' +
               'font-size="24" text-anchor="start" dominant-baseline="auto">' +
               this._escapeXml(opts.unicode) + '</text>';
      }

      svg += '</svg>';
      return svg;
    },

    /**
     * 将卦象数据渲染到指定容器
     *
     * @param {string|Element} container - CSS 选择器或 DOM 元素
     * @param {Array} lines - 六爻数据
     * @param {Object} opts - 可选配置
     */
    renderTo: function (container, lines, opts) {
      var el = (typeof container === 'string') ?
               document.querySelector(container) : container;
      if (!el) return;
      el.innerHTML = this.render(lines, opts);
    },

    /**
     * 从 line values (6/7/8/9) 创建 lines 数据
     */
    linesFromValues: function (values) {
      var RESULT_MAP = {
        6: { is_yang: false, changing: true },
        7: { is_yang: true,  changing: false },
        8: { is_yang: false, changing: false },
        9: { is_yang: true,  changing: true }
      };
      var POSITION_NAMES = { 1: '初', 2: '二', 3: '三', 4: '四', 5: '五', 6: '上' };
      var lines = [];
      for (var i = 0; i < values.length; i++) {
        var pos = i + 1;
        var info = RESULT_MAP[values[i]] || { is_yang: true, changing: false };
        var yao = info.is_yang ? '九' : '六';
        var name = pos === 1 ? '初' + yao :
                   pos === 6 ? '上' + yao :
                   yao + (['', '二', '三', '四', '五'][pos - 1]);
        lines.push({
          position: pos,
          name: name,
          is_yang: info.is_yang,
          changing: info.changing
        });
      }
      return lines;
    },

    /**
     * XML 转义
     */
    _escapeXml: function (str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&apos;');
    }
  };

  // 暴露全局
  window.HexagramRenderer = HexagramRenderer;

  // 自动渲染带有 data-hexagram-lines 属性的元素
  document.addEventListener('DOMContentLoaded', function () {
    var els = document.querySelectorAll('[data-hexagram-lines]');
    els.forEach(function (el) {
      try {
        var data = JSON.parse(el.getAttribute('data-hexagram-lines'));
        var opts = {};
        if (el.getAttribute('data-hexagram-name')) {
          opts.name = el.getAttribute('data-hexagram-name');
        }
        if (el.getAttribute('data-hexagram-unicode')) {
          opts.unicode = el.getAttribute('data-hexagram-unicode');
        }
        var values = data.values || data;
        var lines = HexagramRenderer.linesFromValues(values);
        HexagramRenderer.renderTo(el, lines, opts);
      } catch (e) {
        console.warn('Hexagram render error:', e);
      }
    });
  });
})();
