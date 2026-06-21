/**
 * 主题切换 — Theme Toggle
 * 支持亮色/暗色主题切换，持久化到 localStorage。
 */
(function () {
  'use strict';

  const STORAGE_KEY = 'iching-theme';
  const ATTR = 'data-theme';
  const DARK = 'dark';
  const LIGHT = 'light';

  /**
   * 获取当前主题
   */
  function getTheme() {
    return document.documentElement.getAttribute(ATTR) || LIGHT;
  }

  /**
   * 设置主题并持久化
   */
  function setTheme(theme) {
    document.documentElement.setAttribute(ATTR, theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (e) {
      // localStorage 不可用时忽略
    }
    // 更新切换按钮图标
    updateToggleButton(theme);
  }

  /**
   * 切换主题
   */
  function toggleTheme() {
    const current = getTheme();
    const next = current === DARK ? LIGHT : DARK;
    setTheme(next);
  }

  /**
   * 更新切换按钮图标
   */
  function updateToggleButton(theme) {
    const btns = document.querySelectorAll('.theme-toggle');
    btns.forEach(function (btn) {
      btn.textContent = theme === DARK ? '☀' : '🌙';
      btn.setAttribute('aria-label', theme === DARK ? '切换亮色主题' : '切换暗色主题');
    });
  }

  /**
   * 初始化主题
   */
  function initTheme() {
    var saved = LIGHT;
    try {
      saved = localStorage.getItem(STORAGE_KEY) || LIGHT;
    } catch (e) {
      // ignore
    }
    // 检查系统偏好
    if (saved === LIGHT) {
      var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      if (prefersDark) {
        saved = DARK;
      }
    }
    setTheme(saved);
  }

  /**
   * 绑定切换事件
   */
  function bindToggle() {
    document.addEventListener('click', function (e) {
      var target = e.target.closest('.theme-toggle');
      if (target) {
        toggleTheme();
      }
    });
  }

  // DOM 就绪后执行
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      initTheme();
      bindToggle();
    });
  } else {
    initTheme();
    bindToggle();
  }
})();
