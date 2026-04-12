import requests
import time
import random
import re
from bs4 import BeautifulSoup


class AIWorker:
    def __init__(self, master_url="http://localhost:5000"):
        self.master_url = master_url
        self.ua_list = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/537.36",
        ]

    def run(self):
        print(f"❖ Python AI-Worker 启动，正在监听 Master: {self.master_url} ❖")
        while True:
            try:
                task = self.pull_task()
                if not task:
                    time.sleep(5)
                    continue

                print(f"接收任务: [{task['id']}] {task['url']}")
                result = self.execute_ai_task(task)
                self.submit_result(task["url"], result)
                print("AI 结果已提交")
            except Exception as e:
                print(f"错误: {e}. 10秒后重试...")
                time.sleep(10)

    def pull_task(self):
        resp = requests.get(f"{self.master_url}/task/get")
        return resp.json() if resp.status_code == 200 else None

    def execute_ai_task(self, task):
        headers = {"User-Agent": random.choice(self.ua_list)}
        resp = requests.get(task["url"], headers=headers, timeout=20)
        soup = BeautifulSoup(resp.text, "html.parser")

        # 移除脚本和样式
        for script in soup(["script", "style"]):
            script.decompose()

        text = soup.get_text()
        # 模拟 AI 提取关键词和摘要
        lines = [
            line.strip()
            for row in text.splitlines()
            for line in row.split("  ")
            if line.strip()
        ]
        clean_text = " ".join(lines[:20])  # 取前20行作为摘要

        # 提取链接发现新任务
        if task["depth"] < 2:
            links = [
                a["href"]
                for a in soup.find_all("a", href=True)
                if a["href"].startswith("http")
            ]
            self.report_new_tasks(links[:10], task["depth"] + 1)

        return {
            "worker_lang": "python",
            "ai_summary": clean_text[:200] + "...",
            "keywords": list(set(re.findall(r"\w{4,}", clean_text)))[:5],
            "status_code": resp.status_code,
        }

    def report_new_tasks(self, links, depth):
        tasks = [{"url": link, "priority": 3, "depth": depth} for link in links]
        requests.post(f"{self.master_url}/task/add", json=tasks)

    def submit_result(self, url, data):
        payload = {"url": url, "status": "completed", "data": data}
        requests.post(f"{self.master_url}/task/submit", json=payload)


if __name__ == "__main__":
    AIWorker().run()
