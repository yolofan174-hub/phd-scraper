import os
import requests
from datetime import datetime

KEYWORDS = [
    "single-cell", "single cell", "sequencing", "NGS",
    "digital PCR", "dPCR", "genomics", "transcriptomics",
    "molecular biology", "bio-rad", "library preparation"
]

EURAXESS_API_URL = "https://euraxess.ec.europa.eu/api/jobs/search"

def fetch_jobs():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    payload = {
        "researcherProfiles": ["R1"],
        "sortBy": "newest",
        "pageSize": 50
    }
    try:
        res = requests.post(EURAXESS_API_URL, json=payload, headers=headers, timeout=15)
        return res.json().get("results", []) if res.status_code == 200 else []
    except Exception as e:
        print(f"请求失败: {e}")
        return []

def filter_jobs(job_list):
    matched = []
    now = datetime.now()
    for job in job_list:
        title = job.get("title", "").lower()
        desc = job.get("description", "").lower()
        text = f"{title} {desc}"
        
        # 关键词匹配
        if not any(kw.lower() in text for kw in KEYWORDS):
            continue
            
        # 筛选近 3 天内发布的岗位
        pub_date_str = job.get("publicationDate", "")
        if pub_date_str:
            try:
                pub_date = datetime.strptime(pub_date_str[:10], "%Y-%m-%d")
                if (now - pub_date).days > 3:
                    continue
            except ValueError:
                pass

        matched.append(job)
    return matched

def send_wechat(jobs):
    sendkey = os.environ.get("SERVERCHAN_KEY")
    if not sendkey:
        print("未设置 SERVERCHAN_KEY，跳过微信推送。")
        return

    if not jobs:
        title = "【PhD岗位巡检】近 3 天暂无更新"
        content = "今天没有筛选到符合背景的新岗位，继续加油！"
    else:
        title = f"【PhD岗位巡检】发现 {len(jobs)} 个匹配岗位！"
        content_lines = []
        for i, j in enumerate(jobs, 1):
            content_lines.append(f"### {i}. {j.get('title')}\n")
            content_lines.append(f"- **国家**: {j.get('country')}")
            content_lines.append(f"- **机构**: {j.get('organisation')}")
            content_lines.append(f"- **截止日期**: {j.get('deadline')}")
            content_lines.append(f"- [点击查看详情/申请]({j.get('url')})\n\n---\n")
        content = "\n".join(content_lines)

    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    requests.post(url, data={"title": title, "desp": content})

if __name__ == "__main__":
    jobs = fetch_jobs()
    matched = filter_jobs(jobs)
    send_wechat(matched)
