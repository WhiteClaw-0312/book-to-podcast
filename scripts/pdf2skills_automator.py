"""
pdf2skills 浏览器自动化脚本
使用 Playwright 自动操作浏览器上传 PDF 并下载生成的 Skill
"""

import asyncio
import time
from pathlib import Path
from playwright.async_api import async_playwright


class PDF2SkillsAutomator:
    """pdf2skills 浏览器自动化"""
    
    BASE_URL = "https://pdf2skills.memect.cn"
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.page = None
    
    async def start(self):
        """启动浏览器"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        self.page = await self.context.new_page()
        print("✅ 浏览器启动成功")
    
    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print("✅ 浏览器已关闭")
    
    async def upload_pdf(self, pdf_path: str) -> bool:
        """
        上传 PDF 文件到 pdf2skills
        
        Args:
            pdf_path: PDF 文件路径
        
        Returns:
            是否上传成功
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            print(f"❌ 文件不存在: {pdf_path}")
            return False
        
        print(f"📄 准备上传: {pdf_path.name}")
        
        try:
            # 访问网站
            print(f"🌐 访问 {self.BASE_URL}")
            await self.page.goto(self.BASE_URL, wait_until="networkidle", timeout=60000)
            
            # 等待页面加载
            await self.page.wait_for_timeout(2000)
            
            # 查找上传按钮（需要根据实际网站结构调整）
            # 常见的选择器：
            # - input[type="file"]
            # - button:has-text("上传")
            # - .upload-area
            
            upload_selectors = [
                'input[type="file"]',
                'button:has-text("上传")',
                '.upload-btn',
                '#upload',
                '[data-testid="upload"]'
            ]
            
            upload_element = None
            for selector in upload_selectors:
                try:
                    upload_element = await self.page.query_selector(selector)
                    if upload_element:
                        print(f"✅ 找到上传元素: {selector}")
                        break
                except:
                    continue
            
            if not upload_element:
                print("❌ 未找到上传按钮，页面可能需要登录或结构已变化")
                # 截图保存
                await self.page.screenshot(path="debug_upload_page.png")
                print("📸 已保存截图: debug_upload_page.png")
                return False
            
            # 上传文件
            if await upload_element.get_attribute("type") == "file":
                await upload_element.set_input_files(str(pdf_path))
            else:
                # 点击上传按钮，然后处理文件选择
                await upload_element.click()
                file_input = await self.page.query_selector('input[type="file"]')
                if file_input:
                    await file_input.set_input_files(str(pdf_path))
            
            print("📤 文件上传中...")
            
            # 等待上传完成
            await self.page.wait_for_timeout(5000)
            
            return True
            
        except Exception as e:
            print(f"❌ 上传失败: {e}")
            await self.page.screenshot(path="debug_error.png")
            return False
    
    async def wait_for_conversion(self, timeout: int = 1800) -> bool:
        """
        等待转换完成
        
        Args:
            timeout: 超时时间（秒），默认30分钟
        
        Returns:
            是否转换成功
        """
        print("⏳ 等待转换完成...")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # 检查是否有下载按钮或完成提示
                download_selectors = [
                    'button:has-text("下载")',
                    'a:has-text("下载")',
                    '.download-btn',
                    '#download',
                    '[data-testid="download"]',
                    ':has-text("转换完成")',
                    ':has-text("生成成功")'
                ]
                
                for selector in download_selectors:
                    try:
                        element = await self.page.query_selector(selector)
                        if element:
                            print(f"✅ 转换完成！")
                            return True
                    except:
                        continue
                
                # 检查进度
                progress = await self.page.query_selector('.progress, [role="progressbar"]')
                if progress:
                    value = await progress.get_attribute("aria-valuenow")
                    if value:
                        print(f"📊 进度: {value}%", end="\r")
                
                await self.page.wait_for_timeout(5000)
                
            except Exception as e:
                print(f"⚠️ 检查状态时出错: {e}")
                await self.page.wait_for_timeout(5000)
        
        print(f"\n❌ 转换超时（{timeout}秒）")
        return False
    
    async def download_skill(self, output_dir: str) -> bool:
        """
        下载生成的 Skill
        
        Args:
            output_dir: 输出目录
        
        Returns:
            是否下载成功
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        print(f"📥 下载 Skill 到: {output_path}")
        
        try:
            # 查找下载按钮
            download_selectors = [
                'button:has-text("下载")',
                'a:has-text("下载")',
                '.download-btn',
                '#download'
            ]
            
            download_btn = None
            for selector in download_selectors:
                try:
                    download_btn = await self.page.query_selector(selector)
                    if download_btn:
                        break
                except:
                    continue
            
            if not download_btn:
                print("❌ 未找到下载按钮")
                return False
            
            # 处理下载
            async with self.page.expect_download() as download_info:
                await download_btn.click()
            
            download = await download_info.value
            
            # 保存文件
            save_path = output_path / download.suggested_filename
            await download.save_as(save_path)
            
            print(f"✅ Skill 已下载: {save_path}")
            return True
            
        except Exception as e:
            print(f"❌ 下载失败: {e}")
            return False


async def convert_pdf_to_skill(
    pdf_path: str,
    output_dir: str,
    headless: bool = True
) -> bool:
    """
    将 PDF 转换为 Skill
    
    Args:
        pdf_path: PDF 文件路径
        output_dir: 输出目录
        headless: 是否无头模式
    
    Returns:
        是否成功
    """
    automator = PDF2SkillsAutomator(headless=headless)
    
    try:
        await automator.start()
        
        # 上传 PDF
        if not await automator.upload_pdf(pdf_path):
            return False
        
        # 等待转换
        if not await automator.wait_for_conversion():
            return False
        
        # 下载 Skill
        if not await automator.download_skill(output_dir):
            return False
        
        return True
        
    finally:
        await automator.close()


# 同步接口
def pdf_to_skill(pdf_path: str, output_dir: str, headless: bool = True) -> bool:
    """
    将 PDF 转换为 Skill（同步版本）
    
    使用示例:
        success = pdf_to_skill(
            "data/books/无语问上帝.pdf",
            "data/skills/",
            headless=False  # 调试时显示浏览器
        )
    """
    return asyncio.run(convert_pdf_to_skill(pdf_path, output_dir, headless))


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python pdf2skills_automator.py <pdf_path> [output_dir]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "data/skills/"
    
    print(f"PDF 转 Skill")
    print(f"输入: {pdf_path}")
    print(f"输出: {output_dir}")
    
    success = pdf_to_skill(pdf_path, output_dir, headless=False)
    
    if success:
        print("🎉 转换成功！")
    else:
        print("❌ 转换失败")
        sys.exit(1)