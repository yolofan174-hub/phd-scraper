import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# 匹配关键词库（涵盖分子生物学、测序技术及生命科学大类）
KEYWORDS = [
    "single-cell", "single cell", "sequencing", "ngs", "pcr", "dpcr", 
    "digital pcr", "library prep", "genomics", "transcriptomics", 
    "spatial transcriptomics", "omics", "microfluidics", "flow cytometry",
    "molecular biology", "cell biology", "biochemistry", "cancer research", 
    "immunology", "biomedical", "biotechnology", "genetics"
]

EURAXESS_API_URL = "https://euraxess.ec.europa.eu/api/jobs/search"
# AcademicTransfer 官方 RSS Feed (自动包含最新招聘岗位)
ACADEMIC_TRANSFER_RSS = "https://www.academictransfer.com/en/rss/"

def fetch_euraxess_jobs():
    """抓取 EURAXESS 官方 API"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    payload = {
        "researcherProfiles": ["R1"],  # PhD 级别
        "sortBy": "newest",
        "pageSize": 100
    }
    jobs = []
    try:
        res = requests.post(EURAXESS_API_URL, json=payload, headers=headers, timeout=15)
        if res.status_code == 200:
            for item in res.json().get("results", []):
                jobs.append({
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "country": item.get("country", "欧洲多国"),
                    "organisation": item.get("organisation", "未标识机构"),
                    "deadline": item.get("deadline", "详见官网"),
                    "url": item.get("url", ""),
                    "source": "EURAXESS"
                })
    except Exception as e:
        print(f"EURAXESS 请求失败: {e}")
    return jobs

def fetch_academic_transfer_jobs():
    """抓取 AcademicTransfer (荷兰/欧洲) RSS 数据"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    jobs = []
    try:
        res = requests.get(ACADEMIC_TRANSFER_RSS, headers=headers, timeout=15)
        if res.status_code == 200:
            root = ET.fromstring(res.content)
            # 解析 RSS 节点
            for item in root.findall(".//item"):
                title = item.findtext("title", "")
                description = item.findtext("description", "")
                link = item.findtext("link", "")
                
                # 筛选包含 PhD/Doctoral 相关的岗位
                if any(phd_kw in title.lower() or phd_kw in description.lower() for phd_kw in ["phd", "doctoral", "candidate", "researcher"]):
                    jobs.append({
                        "title": title,
                        "description": description,
                        "country": "Netherlands",
                        "organisation": "Dutch Research Inst.",
                        "deadline": "详见链接",
                        "url": link,
                        "source": "AcademicTransfer"
                    })
    except Exception as e:
        print(f"AcademicTransfer 请求失败: {e}")
    return jobs

def filter_and_deduplicate(job_list):
    """过滤关键词并根据 URL 去重"""
    matched = []
    seen_urls = set()
    
    for job in job_list:
        url = job.get("url", "")
        if not url or url in seen_urls:
            continue
            
        full_text = f"{job['title']} {job['description']}".lower()
        matched_kws = [kw for kw in KEYWORDS if kw in full_text]
        
        if matched_kws:
            job["hit_keywords"] = matched_kws[:3]
            matched.append(job)
            seen_urls.add(url)
            
    return matched

def send_wechat(jobs):
    sendkey = os.environ.get("SERVERCHAN_KEY")
    if not sendkey:
        print("未设置 SERVERCHAN_KEY，跳过微信推送。")
        return

    if not jobs:
        title = "【多源 PhD 巡检】近期暂无符合背景的新岗位"
        content = "已检索 EURAXESS 及 AcademicTransfer，未发现新匹配项。脚本稳定运行中！"
    else:
        title = f"【多源 PhD 巡检】发现 {len(jobs)} 个匹配岗位！"
        content_lines = []
        for i, j in enumerate(jobs, 1):
            kws = ", ".join(j.get("hit_keywords", []))
            content_lines.append(f"### {i}. [{j['source']}] {j['title']}\n")
            content_lines.append(f"- **国家**: {j['country']}")
            content_lines.append(f"- **机构**: {j['organisation']}")
            content_lines.append(f"- **匹配词**: `{kws}`")
            content_lines.append(f"- **截止日期**: {j['deadline']}")
            content_lines.append(f"- [点击查看详情/直接申请]({j['url']})\n\n---\n")
        content = "\n".join(content_lines)

    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    requests.post(url, data={"title": title, "desp": content})

if __name__ == "__main__":
    all_jobs = []
    all_jobs.extend(fetch_euraxess_jobs())
    all_jobs.extend(fetch_academic_transfer_jobs())
    
    final_jobs = filter_and_deduplicate(all_jobs)
    send_wechat(final_jobs)
