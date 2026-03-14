#!/usr/bin/env python3
"""
枕边书 前后端联调测试
使用 Playwright 模拟真实用户操作
"""

import asyncio
import time
import json
from playwright.async_api import async_playwright

# 配置
FRONTEND_URL = "https://whiteclaw-0312.github.io/book-to-podcast/"
BACKEND_URL = "https://139.196.211.206"
API_KEY = "pk_c12ce60b7fd64bf1aea3fa39"
TEST_PDF = "/tmp/test_book.pdf"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def log(msg, level="info"):
    colors = {"info": Colors.BLUE, "pass": Colors.GREEN, "fail": Colors.RED, "warn": Colors.YELLOW}
    print(f"{colors.get(level, '')}{msg}{Colors.END}")

async def test_frontend_load(page):
    """测试1: 前端页面加载"""
    log("\n[测试1] 前端页面加载", "info")
    
    try:
        # 访问前端页面
        await page.goto(FRONTEND_URL, wait_until="networkidle", timeout=30000)
        
        # 等待 Vue 应用加载
        await page.wait_for_selector("h1", timeout=10000)
        
        # 检查标题
        title = await page.locator("h1").first.text_content()
        if "枕边书" in title:
            log(f"  ✅ 页面标题正确: {title}", "pass")
        else:
            log(f"  ❌ 页面标题错误: {title}", "fail")
            return False
        
        # 检查在线状态
        status_badge = await page.locator(".status-badge").text_content()
        if "在线" in status_badge:
            log(f"  ✅ 后端连接正常: {status_badge}", "pass")
        else:
            log(f"  ⚠️ 后端状态: {status_badge}", "warn")
        
        return True
        
    except Exception as e:
        log(f"  ❌ 页面加载失败: {e}", "fail")
        return False

async def test_api_key_input(page):
    """测试2: API Key 输入"""
    log("\n[测试2] API Key 输入", "info")
    
    try:
        # 找到 API Key 输入框
        api_key_input = page.locator("input[placeholder*='pk_']").first
        
        if not await api_key_input.is_visible():
            log(f"  ❌ 未找到 API Key 输入框", "fail")
            return False
        
        # 输入 API Key
        await api_key_input.fill(API_KEY)
        await asyncio.sleep(0.5)
        
        # 验证输入
        value = await api_key_input.input_value()
        if value == API_KEY:
            log(f"  ✅ API Key 输入成功", "pass")
        else:
            log(f"  ❌ API Key 输入失败", "fail")
            return False
        
        return True
        
    except Exception as e:
        log(f"  ❌ API Key 输入失败: {e}", "fail")
        return False

async def test_start_button(page):
    """测试3: 开始使用按钮"""
    log("\n[测试3] 开始使用按钮", "info")
    
    try:
        # 找到"开始使用"按钮
        start_button = page.locator("button:has-text('开始使用')").first
        
        if not await start_button.is_visible():
            log(f"  ❌ 未找到开始使用按钮", "fail")
            return False
        
        # 检查按钮状态（需要先输入 API Key）
        is_disabled = await start_button.is_disabled()
        if is_disabled:
            log(f"  ⚠️ 按钮被禁用（需要先输入 API Key）", "warn")
        else:
            log(f"  ✅ 按钮可点击", "pass")
        
        return True
        
    except Exception as e:
        log(f"  ❌ 按钮检查失败: {e}", "fail")
        return False

async def test_navigate_to_upload(page):
    """测试4: 导航到上传页面"""
    log("\n[测试4] 导航到上传页面", "info")
    
    try:
        # 确保 API Key 已输入
        api_key_input = page.locator("input[placeholder*='pk_']").first
        await api_key_input.fill(API_KEY)
        
        # 点击开始使用
        start_button = page.locator("button:has-text('开始使用')").first
        await start_button.click()
        
        # 等待跳转
        await page.wait_for_url("**/upload**", timeout=10000)
        
        # 检查上传页面元素
        upload_title = await page.locator("h2:has-text('上传')").text_content()
        if "上传" in upload_title:
            log(f"  ✅ 成功跳转到上传页面", "pass")
        else:
            log(f"  ❌ 上传页面标题错误", "fail")
            return False
        
        return True
        
    except Exception as e:
        log(f"  ❌ 导航失败: {e}", "fail")
        return False

async def test_upload_zone(page):
    """测试5: 上传区域检查"""
    log("\n[测试5] 上传区域检查", "info")
    
    try:
        # 检查上传区域
        upload_zone = page.locator(".upload-zone, [class*='upload']").first
        
        if await upload_zone.is_visible():
            log(f"  ✅ 上传区域可见", "pass")
        else:
            log(f"  ❌ 上传区域不可见", "fail")
            return False
        
        # 检查文件输入
        file_input = page.locator("input[type='file']").first
        if await file_input.count() > 0:
            log(f"  ✅ 文件输入存在", "pass")
        else:
            log(f"  ❌ 文件输入不存在", "fail")
            return False
        
        return True
        
    except Exception as e:
        log(f"  ❌ 上传区域检查失败: {e}", "fail")
        return False

async def test_balance_page(page):
    """测试6: 余额查询页面"""
    log("\n[测试6] 余额查询页面", "info")
    
    try:
        # 导航到首页
        await page.goto(FRONTEND_URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_selector("h1", timeout=10000)
        
        # 检查是否有余额查询按钮
        balance_button = page.locator("button:has-text('余额'), a:has-text('余额')").first
        
        if await balance_button.is_visible():
            await balance_button.click()
            await asyncio.sleep(1)
            
            # 检查是否跳转到余额页面
            url = page.url
            if "balance" in url:
                log(f"  ✅ 成功跳转到余额页面", "pass")
            else:
                log(f"  ⚠️ 未跳转到余额页面: {url}", "warn")
        else:
            log(f"  ⚠️ 未找到余额查询按钮", "warn")
        
        return True
        
    except Exception as e:
        log(f"  ❌ 余额页面测试失败: {e}", "fail")
        return False

async def test_api_connectivity(page):
    """测试7: API 连通性"""
    log("\n[测试7] API 连通性", "info")
    
    try:
        # 直接测试后端 API
        response = await page.request.get(f"{BACKEND_URL}/health")
        
        if response.ok:
            data = await response.json()
            log(f"  ✅ 后端 API 正常 (版本: {data.get('version')})", "pass")
        else:
            log(f"  ❌ 后端 API 异常: {response.status}", "fail")
            return False
        
        # 测试余额 API
        response = await page.request.get(f"{BACKEND_URL}/api/keys/{API_KEY}/balance")
        
        if response.ok:
            data = await response.json()
            log(f"  ✅ 余额查询正常 (余额: {data.get('balance')}次)", "pass")
        else:
            log(f"  ❌ 余额查询失败", "fail")
            return False
        
        return True
        
    except Exception as e:
        log(f"  ❌ API 连通性测试失败: {e}", "fail")
        return False

async def take_screenshot(page, name):
    """截图"""
    try:
        await page.screenshot(path=f"/tmp/{name}.png")
        log(f"  📸 截图已保存: /tmp/{name}.png", "info")
    except:
        pass

async def run_all_tests():
    """运行所有测试"""
    log("="*60, "info")
    log("枕边书 前后端联调测试", "info")
    log("="*60, "info")
    
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(
            headless=True,
            args=['--ignore-certificate-errors']
        )
        
        context = await browser.new_context(
            ignore_https_errors=True,
            viewport={"width": 1280, "height": 720}
        )
        
        page = await context.new_page()
        
        results = []
        
        try:
            # 1. 页面加载
            results.append(("前端页面加载", await test_frontend_load(page)))
            await take_screenshot(page, "01_homepage")
            
            # 2. API Key 输入
            results.append(("API Key 输入", await test_api_key_input(page)))
            
            # 3. 开始使用按钮
            results.append(("开始使用按钮", await test_start_button(page)))
            
            # 4. 导航到上传页面
            results.append(("导航到上传页面", await test_navigate_to_upload(page)))
            await take_screenshot(page, "02_upload_page")
            
            # 5. 上传区域
            results.append(("上传区域检查", await test_upload_zone(page)))
            
            # 6. 余额页面
            results.append(("余额查询页面", await test_balance_page(page)))
            await take_screenshot(page, "03_balance_page")
            
            # 7. API 连通性
            results.append(("API 连通性", await test_api_connectivity(page)))
            
        except Exception as e:
            log(f"\n❌ 测试执行异常: {e}", "fail")
        
        finally:
            await browser.close()
        
        # 汇总
        log("\n" + "="*60, "info")
        log("测试结果汇总", "info")
        log("="*60, "info")
        
        passed = sum(1 for _, r in results if r)
        total = len(results)
        
        for name, success in results:
            status = "✅ 通过" if success else "❌ 失败"
            log(f"  {name}: {status}", "pass" if success else "fail")
        
        log("-"*60, "info")
        log(f"总计: {passed}/{total} 通过", "pass" if passed == total else "fail")
        
        return passed == total

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)