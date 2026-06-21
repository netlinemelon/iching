"""
自动化截图脚本 — 为宣传图文批量生成页面截图。
用法: python scripts/screenshots.py

前提: pip install playwright && playwright install chromium
"""

import subprocess
import time
import sys
import socket
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "screenshots"


def _find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_server(port: int):
    print(f"[1/3] 启动服务器 (端口 {port})...")
    env = {"HOST": "127.0.0.1", "PORT": str(port), "DEBUG": "false"}
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={**__import__("os").environ, **env},
    )

    # 等待服务就绪
    import urllib.request
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=2)
            print("  服务器就绪")
            return proc
        except Exception:
            time.sleep(0.5)
    proc.terminate()
    raise RuntimeError("服务器启动超时")


def stop_server(proc):
    print("\n[3/3] 关闭服务器...")
    proc.terminate()
    proc.wait()


def capture_pages(port: int):
    from playwright.sync_api import sync_playwright

    BASE_URL = f"http://127.0.0.1:{port}"
    OUTPUT_DIR.mkdir(exist_ok=True)

    pages_to_capture = [
        ("/", "01-home"),
        ("/divine/", "02-divine-index"),
        ("/divine/coin", "03-coin-method"),
        ("/divine/yarrow", "04-yarrow-method"),
        ("/divine/time", "05-time-method"),
        ("/divine/number", "06-number-method"),
        ("/divine/plum-blossom", "07-plum-blossom"),
        ("/hexagram/", "08-hexagram-grid"),
        ("/hexagram/1", "09-hexagram-detail"),
        ("/hexagram/search?q=乾", "10-hexagram-search"),
        ("/study/", "11-study-index"),
        ("/study/trigrams", "12-study-trigrams"),
        ("/study/methods", "13-study-methods"),
        ("/study/interpretation", "14-study-interpretation"),
        ("/history/", "15-history"),
    ]

    print(f"[2/3] 截图 ({len(pages_to_capture)} 页面 × 2 主题)...")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2,
        )
        page = context.new_page()

        # 先访问一次首页确认 CSS 正常加载
        page.goto(BASE_URL + "/", wait_until="networkidle")
        page.wait_for_timeout(1000)
        sheet_count = page.evaluate(
            "() => document.styleSheets.length"
        )
        print(f"  样式表数量: {sheet_count}")

        for path, name in pages_to_capture:
            url = f"{BASE_URL}{path}"
            print(f"  [{name}] {url}")

            # 亮色主题
            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(800)
            page.evaluate(
                "document.documentElement.setAttribute('data-theme', 'light')"
            )
            page.wait_for_timeout(300)
            page.screenshot(
                path=str(OUTPUT_DIR / f"{name}-light.png"),
                full_page=True,
            )

            # 暗色主题
            page.evaluate(
                "document.documentElement.setAttribute('data-theme', 'dark')"
            )
            page.wait_for_timeout(300)
            page.screenshot(
                path=str(OUTPUT_DIR / f"{name}-dark.png"),
                full_page=True,
            )

        # --- 占卜结果页（POST 触发占卜） ---
        print("  [16-divination-result] 执行占卜...")
        page.goto(f"{BASE_URL}/divine/coin", wait_until="networkidle")
        page.wait_for_timeout(800)

        # 通过 JS fetch 触发 POST，然后跟随重定向到结果页
        result_url = page.evaluate(f"""
            async () => {{
                const resp = await fetch('{BASE_URL}/divine/coin/toss', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/x-www-form-urlencoded' }},
                    body: 'question=测试占卜',
                    redirect: 'manual',
                }});
                const location = resp.headers.get('Location') || resp.url;
                return location;
            }}
        """)
        # 如果返回相对路径，补全
        if result_url.startswith("/"):
            result_url = f"{BASE_URL}{result_url}"
        page.goto(result_url, wait_until="networkidle")
        page.wait_for_timeout(1000)

        # 结果页 — 亮色
        page.evaluate("document.documentElement.setAttribute('data-theme', 'light')")
        page.wait_for_timeout(500)
        page.screenshot(
            path=str(OUTPUT_DIR / "16-result-light.png"),
            full_page=True,
        )
        # 结果页 — 暗色
        page.evaluate("document.documentElement.setAttribute('data-theme', 'dark')")
        page.wait_for_timeout(300)
        page.screenshot(
            path=str(OUTPUT_DIR / "16-result-dark.png"),
            full_page=True,
        )

        browser.close()

    files = sorted(OUTPUT_DIR.glob("*.png"))
    print(f"\n  完成! 生成了 {len(files)} 个截图:")
    for f in files:
        size_kb = f.stat().st_size / 1024
        print(f"    {f.name} ({size_kb:.0f} KB)")


def main():
    port = _find_free_port()
    server = start_server(port)
    try:
        capture_pages(port)
    finally:
        stop_server(server)


if __name__ == "__main__":
    main()
