#!/usr/bin/env python3
"""
枕边书 API 端到端测试
测试所有核心功能是否正常运行
"""

import requests
import time
import json
import sys
from pathlib import Path

# 配置
API_BASE = "https://139.196.211.206"
API_KEY = "pk_c12ce60b7fd64bf1aea3fa39"
TEST_PDF = "/tmp/test_book.pdf"

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def log(msg, level="info"):
    colors = {"info": Colors.BLUE, "pass": Colors.GREEN, "fail": Colors.RED, "warn": Colors.YELLOW}
    print(f"{colors.get(level, '')}{msg}{Colors.END}")

def api_get(path):
    """GET 请求"""
    try:
        r = requests.get(f"{API_BASE}{path}", verify=False, timeout=30)
        return r.status_code, r.json() if r.text else {}
    except Exception as e:
        return 0, {"error": str(e)}

def api_post(path, data=None, files=None):
    """POST 请求"""
    try:
        if files:
            r = requests.post(f"{API_BASE}{path}", files=files, data=data, verify=False, timeout=60)
        else:
            r = requests.post(f"{API_BASE}{path}", json=data, verify=False, timeout=60)
        return r.status_code, r.json() if r.text else {}
    except Exception as e:
        return 0, {"error": str(e)}

# 测试用例
def test_health():
    """测试1: 健康检查"""
    log("\n[测试1] 健康检查", "info")
    code, data = api_get("/health")
    
    if code == 200 and data.get("status") == "ok":
        log(f"  ✅ 服务正常运行 (版本: {data.get('version')})", "pass")
        return True
    else:
        log(f"  ❌ 服务异常: {code} - {data}", "fail")
        return False

def test_balance():
    """测试2: 余额查询"""
    log("\n[测试2] 余额查询", "info")
    code, data = api_get(f"/api/keys/{API_KEY}/balance")
    
    if code == 200:
        balance = data.get("balance", 0)
        used = data.get("total_used", 0)
        log(f"  ✅ 余额: {balance}次, 已用: {used}次", "pass")
        return True, balance
    else:
        log(f"  ❌ 查询失败: {code} - {data}", "fail")
        return False, 0

def test_upload():
    """测试3: PDF上传"""
    log("\n[测试3] PDF上传", "info")
    
    # 创建测试PDF
    if not Path(TEST_PDF).exists():
        log(f"  ⚠️ 测试文件不存在，创建中...", "warn")
        Path(TEST_PDF).write_text("%PDF-1.4\ntest content")
    
    with open(TEST_PDF, "rb") as f:
        files = {"file": ("test_e2e.pdf", f, "application/pdf")}
        data = {"api_key": API_KEY}
        code, resp = api_post("/api/books", data=data, files=files)
    
    if code == 200 and "id" in resp:
        book_id = resp["id"]
        log(f"  ✅ 上传成功 (ID: {book_id})", "pass")
        return True, book_id
    else:
        log(f"  ❌ 上传失败: {code} - {resp}", "fail")
        return False, None

def test_ocr(book_id, timeout=60):
    """测试4: OCR处理"""
    log("\n[测试4] OCR处理", "info")
    log(f"  等待处理 (最长{timeout}秒)...", "info")
    
    start = time.time()
    while time.time() - start < timeout:
        code, data = api_get(f"/api/books/{book_id}")
        
        if data.get("status") == "ready":
            chapters = data.get("total_chapters", 0)
            progress = data.get("ocr_progress", 0)
            log(f"  ✅ OCR完成 (进度: {progress}%, 章节: {chapters})", "pass")
            return True, data
        
        elif data.get("status") == "failed":
            log(f"  ❌ OCR失败: {data.get('error_message')}", "fail")
            return False, data
        
        time.sleep(3)
    
    log(f"  ❌ OCR超时", "fail")
    return False, {}

def test_generate(book_id, chapters=[1]):
    """测试5: 播客生成"""
    log("\n[测试5] 播客生成", "info")
    
    data = {"chapters": chapters, "api_key": API_KEY}
    code, resp = api_post(f"/api/books/{book_id}/generate", data=data)
    
    if code == 200:
        cost = resp.get("cost", 0)
        estimated = resp.get("estimated_time", 0)
        log(f"  ✅ 开始生成 (消耗: {cost}次, 预计: {estimated}秒)", "pass")
        return True
    else:
        log(f"  ❌ 生成失败: {code} - {resp}", "fail")
        return False

def test_audio_generation(book_id, timeout=300):
    """测试6: 音频生成"""
    log("\n[测试6] 音频生成", "info")
    log(f"  等待生成 (最长{timeout}秒)...", "info")
    
    start = time.time()
    while time.time() - start < timeout:
        code, data = api_get(f"/api/books/{book_id}")
        
        status = data.get("status")
        audio_progress = data.get("audio_progress", 0)
        
        if status == "completed":
            chapters = data.get("chapters", [])
            if chapters and chapters[0].get("has_audio"):
                duration = chapters[0].get("duration", 0)
                log(f"  ✅ 生成完成 (时长: {duration:.1f}秒)", "pass")
                return True, chapters[0]
            else:
                log(f"  ❌ 无音频文件", "fail")
                return False, {}
        
        elif status == "failed":
            log(f"  ❌ 生成失败: {data.get('error_message')}", "fail")
            return False, {}
        
        # 显示进度
        if audio_progress > 0:
            print(f"\r  进度: {audio_progress}%  ", end="", flush=True)
        
        time.sleep(5)
    
    log(f"\n  ❌ 生成超时", "fail")
    return False, {}

def test_audio_download(book_id, chapter_num=1):
    """测试7: 音频下载"""
    log("\n[测试7] 音频下载", "info")
    
    try:
        r = requests.get(f"{API_BASE}/api/books/{book_id}/chapters/{chapter_num}/audio", 
                        verify=False, timeout=30, stream=True)
        
        if r.status_code == 200:
            # 读取前1KB验证
            chunk = next(r.iter_content(1024), b"")
            if len(chunk) > 0:
                log(f"  ✅ 音频可下载 (响应正常)", "pass")
                return True
            else:
                log(f"  ❌ 音频内容为空", "fail")
                return False
        else:
            log(f"  ❌ 下载失败: {r.status_code}", "fail")
            return False
    except Exception as e:
        log(f"  ❌ 下载异常: {e}", "fail")
        return False

def test_script(book_id, chapter_num=1):
    """测试8: 文稿获取"""
    log("\n[测试8] 文稿获取", "info")
    
    code, data = api_get(f"/api/books/{book_id}/chapters/{chapter_num}/script")
    
    if code == 200 and "dialogues" in data:
        dialogues = data.get("dialogues", [])
        word_count = data.get("word_count", 0)
        log(f"  ✅ 文稿获取成功 (对话: {len(dialogues)}句, 字数: {word_count})", "pass")
        return True
    else:
        log(f"  ❌ 文稿获取失败: {code} - {data}", "fail")
        return False

def test_deduction(initial_balance):
    """测试9: 余额扣减验证"""
    log("\n[测试9] 余额扣减验证", "info")
    
    code, data = api_get(f"/api/keys/{API_KEY}/balance")
    
    if code == 200:
        new_balance = data.get("balance", 0)
        new_used = data.get("total_used", 0)
        deducted = initial_balance - new_balance
        
        if deducted == 1:  # 生成1章，扣1次
            log(f"  ✅ 余额正确扣减 (-{deducted}次, 当前: {new_balance}次)", "pass")
            return True
        else:
            log(f"  ❌ 余额扣减异常 (预期-1, 实际-{deducted})", "fail")
            return False
    else:
        log(f"  ❌ 查询失败", "fail")
        return False

# 主测试流程
def run_all_tests():
    """运行所有测试"""
    log("="*60, "info")
    log("枕边书 API 端到端测试", "info")
    log("="*60, "info")
    
    results = []
    
    # 1. 健康检查
    results.append(("健康检查", test_health()))
    
    # 2. 初始余额
    success, initial_balance = test_balance()
    results.append(("余额查询", success))
    if not success:
        log("\n❌ 无法获取余额，终止测试", "fail")
        return False
    
    # 3. 上传
    success, book_id = test_upload()
    results.append(("PDF上传", success))
    if not success:
        log("\n❌ 上传失败，终止测试", "fail")
        return False
    
    # 4. OCR
    success, book_data = test_ocr(book_id)
    results.append(("OCR处理", success))
    if not success:
        log("\n❌ OCR失败，终止测试", "fail")
        return False
    
    # 5. 生成播客
    success = test_generate(book_id)
    results.append(("播客生成启动", success))
    if not success:
        log("\n❌ 生成启动失败，终止测试", "fail")
        return False
    
    # 6. 等待音频生成
    success, chapter_data = test_audio_generation(book_id)
    results.append(("音频生成", success))
    
    # 7. 音频下载
    results.append(("音频下载", test_audio_download(book_id)))
    
    # 8. 文稿获取
    results.append(("文稿获取", test_script(book_id)))
    
    # 9. 余额扣减
    results.append(("余额扣减", test_deduction(initial_balance)))
    
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
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    success = run_all_tests()
    sys.exit(0 if success else 1)