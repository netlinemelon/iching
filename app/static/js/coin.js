/**
 * 金钱卦 — 铜钱抛掷交互
 *
 * 用 Alpine.js 管理状态，实现：
 * - 6次抛掷，每次抛掷3枚铜钱
 * - 逐爻构建卦象
 * - 抛掷动画
 * - 自动提交
 */

(function () {
  'use strict';

  // 铜钱正面(3) / 反面(2)
  var COIN_FRONT = 3; // 字
  var COIN_BACK = 2;  // 花

  // 结果映射
  var RESULT_MAP = {
    6: { type: '老阴', is_yang: false, changing: true, symbol: 'yin' },
    7: { type: '少阳', is_yang: true,  changing: false, symbol: 'yang' },
    8: { type: '少阴', is_yang: false, changing: false, symbol: 'yin' },
    9: { type: '老阳', is_yang: true,  changing: true,  symbol: 'yang' }
  };

  var POSITION_NAMES = { 1: '初', 2: '二', 3: '三', 4: '四', 5: '五', 6: '上' };

  /**
   * 随机抛掷一枚铜钱
   */
  function tossOne() {
    return Math.random() < 0.5 ? COIN_FRONT : COIN_BACK;
  }

  /**
   * 抛掷三枚铜钱并计算结果
   */
  function tossThree() {
    var c1 = tossOne();
    var c2 = tossOne();
    var c3 = tossOne();
    var sum = c1 + c2 + c3;
    var result = RESULT_MAP[sum];
    return {
      coins: [c1, c2, c3],
      sum: sum,
      result: result,
      // 每枚铜钱的面值显示
      faces: [c1 === COIN_FRONT ? '正' : '反',
              c2 === COIN_FRONT ? '正' : '反',
              c3 === COIN_FRONT ? '正' : '反']
    };
  }

  /**
   * 获取爻名
   */
  function getLineName(position, isYang) {
    var yao = isYang ? '九' : '六';
    if (position === 1) return '初' + yao;
    if (position === 6) return '上' + yao;
    var middle = { 2: '二', 3: '三', 4: '四', 5: '五' };
    return yao + middle[position];
  }

  /**
   * 注册 Alpine.js 组件
   */
  document.addEventListener('alpine:init', function () {
    Alpine.data('coinDivination', function () {
      return {
        // 状态
        step: 'ready', // ready | tossing | done | error
        currentToss: 0,
        maxTosses: 6,
        errorMessage: '',

        // 用户所问之事
        question: '',

        // 每次抛掷结果
        tosses: [],
        // 累积的爻
        lines: [],
        // 当前正在抛掷的铜钱动画
        animating: false,
        currentCoins: null,

        // 计算属性 - 当前已完成的爻数
        get completedCount() {
          return this.lines.length;
        },

        // 是否可以抛掷
        get canToss() {
          return !this.animating && this.completedCount < this.maxTosses;
        },

        // 获取爻的显示符号
        getLineSymbol: function (line) {
          return line.is_yang ? '—' : '- -';
        },

        // 开始抛掷
        startToss: function () {
          if (this.animating || this.completedCount >= this.maxTosses) return;
          this.animating = true;
          this.currentToss = this.completedCount;
          this.doCoinFlip();
        },

        // 执行铜钱翻转动画
        doCoinFlip: function () {
          var self = this;

          // 生成随机结果
          var toss = tossThree();
          var position = self.completedCount + 1;

          // 先显示翻转动画
          self.currentCoins = {
            faces: ['?', '?', '?'],
            flipping: true
          };

          // 动画期间显示随机翻转
          var flipInterval = setInterval(function () {
            if (self.currentCoins && self.currentCoins.flipping) {
              self.currentCoins = {
                faces: [
                  Math.random() < 0.5 ? '正' : '反',
                  Math.random() < 0.5 ? '正' : '反',
                  Math.random() < 0.5 ? '正' : '反'
                ],
                flipping: true
              };
            }
          }, 80);

          // 动画结束后显示真实结果
          setTimeout(function () {
            clearInterval(flipInterval);

            var lineName = getLineName(position, toss.result.is_yang);
            var lineData = {
              position: position,
              name: lineName,
              is_yang: toss.result.is_yang,
              changing: toss.result.changing,
              type: toss.result.type,
              value: toss.sum,
              symbol: toss.result.symbol
            };

            // 显示真实结果
            self.currentCoins = {
              faces: toss.faces,
              values: toss.coins,
              sum: toss.sum,
              result: toss.result,
              flipping: false
            };

            // 短暂延迟后添加到爻列表
            setTimeout(function () {
              self.tosses.push({
                tossNumber: position,
                coins: toss.coins,
                faces: toss.faces,
                sum: toss.sum,
                result: toss.result,
                lineName: lineName
              });
              self.lines.push(lineData);
              self.currentCoins = null;
              self.animating = false;

              // 如果全部完成，自动提交
              if (self.completedCount >= self.maxTosses) {
                self.step = 'done';
                self.autoSubmit();
              }
            }, 400);
          }, 600);
        },

        // 自动提交表单（使用 fetch 实现错误处理）
        autoSubmit: function () {
          var self = this;
          // 延迟提交，让用户看到完整卦象
          setTimeout(function () {
            var form = document.getElementById('coin-form');
            if (!form) return;

            // 填入真实的六爻值
            var values = self.lines.map(function (l) { return l.value; });
            var valuesInput = document.getElementById('coin-values-input');
            var questionInput = document.getElementById('coin-question-input');
            if (valuesInput) valuesInput.value = values.join(',');
            if (questionInput) questionInput.value = self.question;

            // 使用 fetch 异步提交，便于捕获错误
            var formData = new FormData(form);
            fetch(form.action, {
              method: 'POST',
              body: formData
            }).then(function (response) {
              if (response.redirected) {
                // 服务端返回重定向 -> 正常跳转
                window.location.href = response.url;
              } else if (response.ok) {
                // 也可能返回 200 但需要手动跳转
                window.location.href = response.url;
              } else {
                // 服务器返回错误
                return response.text().then(function (text) {
                  throw new Error('服务器返回 ' + response.status + (text ? ': ' + text.substring(0, 100) : ''));
                });
              }
            }).catch(function (err) {
              // 网络/服务器错误 -> 显示错误状态并允许重试
              self.step = 'error';
              self.errorMessage = '提交失败: ' + err.message;
            });
          }, 1000);
        },

        // 重置（重新开始）
        reset: function () {
          this.step = 'ready';
          this.currentToss = 0;
          this.tosses = [];
          this.lines = [];
          this.animating = false;
          this.currentCoins = null;
          this.errorMessage = '';
        },

        // 重试提交
        retrySubmit: function () {
          this.step = 'done';
          this.autoSubmit();
        }
      };
    });
  });
})();
