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
        
        print(f"📄 准备上传: {pdf_path.name} ({pdf_path.stat().st_size / 1024 / 1024:.1f} MB)")
        
        try:
            # 访问网站
            print(f"🌐 访问 {self.BASE_URL}")
            await self.page.goto(self.BASE_URL, wait_until="networkidle", timeout=60000)
            
            # 等待页面加载
            await self.page.wait_for_timeout(2000)
            
            # 截图保存初始页面
            await self.page.screenshot(path="data/pdf2skills_initial.png")
            print("📸 初始页面截图: data/pdf2skills_initial.png")
            
            # 查找文件上传 input
            file_input = await self.page.query_selector('input[type="file"]')
            
            if not file_input:
                print("❌ 未找到文件上传 input")
                return False
            
            print("✅ 找到文件上传 input")
            
            # 上传文件
            await file_input.set_input_files(str(pdf_path))
            print("📤 文件上传中...")
            
            # 等待上传响应
            await self.page.wait_for_timeout(3000)
            
            # 截图保存上传后状态
            await self.page.screenshot(path="data/pdf2skills_uploaded.png")
            print("📸 上传后截图: data/pdf2skills_uploaded.png")
            
            return True
            
        except Exception as e:
            print(f"❌ 上传失败: {e}")
            await self.page.screenshot(path="data/pdf2skills_error.png")
            print("📸 错误截图: data/pdf2skills_error.png")
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
                # 检查是否有 "Launch App" 按钮出现
                launch_btn = await self.page.query_selector('button:has-text("Launch App")')
                if launch_btn:
                    print("✅ 转换完成！发现 Launch App 按钮")
                    return True
                
                # 检查进度条
                progress_bar = await self.page.query_selector('[class*="progress"]')
                if progress_bar:
                    # 尝试获取进度
                    try:
                        width = await progress_bar.evaluate('el => el.style.width || el.offsetWidth')
                        print(f"📊 进度: {width}", end="\r")
                    except:
                        pass
                
                await self.page.wait_for_timeout(5000)
                
            except Exception as e:
                print(f"⚠️ 检查状态时出错: {e}")
                await self.page.wait_for_timeout(5000)
        
        print(f"\n❌ 转换超时（{timeout}秒）")
        return False
    
    async def launch_app(self) -> bool:
        """
        启动转换后的应用
        
        Returns:
            是否成功
        """
        print("🚀 启动应用...")
        
        try:
            # 查找 Launch App 按钮
            launch_btn = await self.page.query_selector('button:has-text("Launch App")')
            
            if not launch_btn:
                print("❌ 未找到 Launch App 按钮")
                return False
            
            # 点击按钮
            await launch_btn.click()
            print("✅ 已点击 Launch App")
            
            # 等待新页面加载
            await self.page.wait_for_timeout(3000)
            
            # 截图
            await self.page.screenshot(path="data/pdf2skills_app.png")
            print("📸 应用页面截图: data/pdf2skills_app.png")
            
            return True
            
        except Exception as e:
            print(f"❌ 启动应用失败: {e}")
            return False
    
    async def get_skill_content(self) -> str:
        """
        获取 Skill 内容
        
        Returns:
            Skill 内容（Markdown 格式）
        """
        print("📖 获取 Skill 内容...")
        
        try:
            # 获取页面内容
            content = await self.page.content()
            
            # 尝试提取主要内容
            # 这里需要根据实际页面结构调整
            main_content = await self.page.query_selector('main, .content, .skill-content, [class*="skill"]')
            
            if main_content:
                text = await main_content.inner_text()
                print(f"✅ 获取到内容: {len(text)} 字符")
                return text
            else:
                print("⚠️ 未找到主要内容区域")
                return ""
                
        except Exception as e:
            print(f"❌ 获取内容失败: {e}")
            return ""


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
        
        # 启动应用
        if not await automator.launch_app():
            return False
        
        # 获取 Skill 内容
        content = await automator.get_skill_content()
        
        if content:
            # 保存内容
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            skill_file = output_path / "skill_content.md"
            
            with open(skill_file, "w", encoding="utf-8") as f:
                f.write(content)
            
            print(f"✅ Skill 内容已保存: {skill_file}")
            return True
        
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