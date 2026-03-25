"""
SuperSpider GitHub 发布自动化脚本
使用 Playwright 自动创建 GitHub 仓库并发布
"""

import asyncio
import os
import subprocess
from playwright.async_api import async_playwright


async def publish_to_github():
    """使用 Playwright 自动发布到 GitHub"""
    
    print("🚀 SuperSpider GitHub 发布自动化")
    print("=" * 50)
    
    # 配置
    github_username = input("请输入 GitHub 用户名：").strip()
    repo_name = "superspider"
    repo_description = "SuperSpider - 四合一爬虫框架集合 (PySpider + RustSpider + GoSpider + JavaSpider)"
    
    if not github_username:
        print("❌ 用户名不能为空")
        return
    
    print(f"\n📦 准备发布到：https://github.com/{github_username}/{repo_name}")
    print("")
    
    async with async_playwright() as p:
        # 启动浏览器
        print("🌐 启动浏览器...")
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()
        
        # 导航到 GitHub 新建仓库页面
        print("📝 导航到 GitHub...")
        await page.goto("https://github.com/new")
        
        # 等待页面加载
        await page.wait_for_load_state("networkidle")
        
        # 检查是否登录
        current_url = page.url
        if "login" in current_url:
            print("⚠️  检测到未登录，请先登录 GitHub")
            print("💡 提示：登录后脚本将继续执行")
            
            # 等待用户登录
            try:
                await page.wait_for_url("https://github.com/new", timeout=60000)
            except:
                print("❌ 登录超时")
                await browser.close()
                return
        
        # 填写仓库信息
        print("✏️  填写仓库信息...")
        
        # 仓库名称
        await page.fill("input#repository_name", repo_name)
        
        # 仓库描述
        await page.fill("input#repository_description", repo_description)
        
        # 公开仓库
        await page.click("input[type='radio'][value='public']")
        
        # 不初始化 README（我们已有自己的文件）
        # 取消勾选 Initialize this repository with a README
        readme_checkbox = await page.query_selector("input#init-readings")
        if readme_checkbox:
            is_checked = await readme_checkbox.is_checked()
            if is_checked:
                await readme_checkbox.uncheck()
        
        print("✅ 仓库信息填写完成")
        
        # 等待用户确认
        input("\n📋 请确认信息无误，按 Enter 键继续创建仓库...")
        
        # 点击创建按钮
        print("🚀 创建仓库...")
        create_button = await page.query_selector("button[type='submit']")
        if create_button:
            await create_button.click()
            
            # 等待跳转
            await page.wait_for_load_state("networkidle")
            
            # 获取新仓库 URL
            repo_url = page.url
            print(f"\n✅ 仓库创建成功！")
            print(f"📦 仓库地址：{repo_url}")
            print("")
        else:
            print("⚠️  可能仓库已存在，请手动检查")
            repo_url = f"https://github.com/{github_username}/{repo_name}"
        
        # 显示推送说明
        print("=" * 50)
        print("📤 现在推送代码到 GitHub...")
        print("")
        print("请在终端执行以下命令：")
        print("")
        print(f"cd {os.getcwd()}")
        print("git remote add origin " + repo_url)
        print("git branch -M main")
        print("git push -u origin main")
        print("")
        
        # 询问是否自动推送
        auto_push = input("是否自动执行 git push？(y/n): ").strip().lower()
        
        if auto_push == 'y':
            print("\n📤 执行 Git 推送...")
            
            try:
                # 检查是否在 git 仓库中
                result = subprocess.run(
                    ["git", "rev-parse", "--git-dir"],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    print("📝 初始化 Git 仓库...")
                    subprocess.run(["git", "init"], check=True)
                
                # 添加远程仓库
                print("🔗 添加远程仓库...")
                subprocess.run(
                    ["git", "remote", "add", "origin", repo_url],
                    check=True,
                    capture_output=True
                )
                
                # 切换到 main 分支
                print("🌿 切换到 main 分支...")
                subprocess.run(["git", "branch", "-M", "main"], check=True)
                
                # 推送
                print("📤 推送代码...")
                subprocess.run(["git", "push", "-u", "origin", "main"], check=True)
                
                print("\n✅ 推送成功！")
                print(f"🌐 查看仓库：{repo_url}")
                
            except subprocess.CalledProcessError as e:
                print(f"\n❌ Git 操作失败：{e}")
                print("\n💡 请手动执行上述 git 命令")
        
        # 关闭浏览器
        print("\n🔒 关闭浏览器...")
        await browser.close()
        
        print("\n" + "=" * 50)
        print("🎉 发布完成！")
        print("=" * 50)
        print("")
        print("下一步建议:")
        print("1. 在 GitHub 仓库页面添加主题标签")
        print("2. 配置 GitHub Actions CI/CD")
        print("3. 添加 Release 版本")
        print("4. 设置仓库保护规则")
        print("")


if __name__ == "__main__":
    print("SuperSpider GitHub 发布工具")
    print("使用 Playwright 自动创建 GitHub 仓库\n")
    
    # 检查 Playwright
    try:
        import playwright
    except ImportError:
        print("❌ Playwright 未安装")
        print("💡 请先安装：pip install playwright")
        print("💡 然后执行：playwright install")
        exit(1)
    
    # 运行
    asyncio.run(publish_to_github())
