"""
FastAPI后端服务器
提供论文数据的API接口
"""
import os
import json
from datetime import datetime, timedelta
from typing import List, Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import FastAPI, Query, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import load_config

# 加载配置
config = load_config('config.yaml')
data_root = config.get('output', {}).get('data_root', 'data')

# 获取API路径前缀，默认为 ai_paper
server_cfg = config.get('server', {})
api_prefix = server_cfg.get('api_prefix', 'ai_paper')
# 确保前缀以 / 开头，但不以 / 结尾
if not api_prefix.startswith('/'):
    api_prefix = '/' + api_prefix
if api_prefix.endswith('/'):
    api_prefix = api_prefix.rstrip('/')

app = FastAPI(title="Paper AI API", version="1.0.0")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建API路由器，添加统一前缀
api_router = APIRouter(prefix=api_prefix)


class PaperInfo(BaseModel):
    """论文信息模型"""
    title: str
    authors: List[str]
    summary: str
    published: str
    categories: List[str]
    primary_category: str
    pdf_url: str
    entry_id: str
    doi: Optional[str] = None
    llm_summary: Optional[str] = None
    content: Optional[str] = None
    markdown_path: Optional[str] = None
    pdf_path: Optional[str] = None


def get_paper_dates():
    """获取所有有论文数据的日期列表"""
    data_path = Path(data_root)
    if not data_path.exists():
        return []

    dates = []
    for item in data_path.iterdir():
        if item.is_dir() and item.name != 'unknown':
            try:
                # 验证是否为有效日期格式
                datetime.strptime(item.name, '%Y-%m-%d')
                dates.append(item.name)
            except ValueError:
                continue

    dates.sort(reverse=True)
    return dates


def load_papers_from_date(date_str: str) -> List[dict]:
    """从指定日期目录加载所有论文"""
    date_dir = Path(data_root) / date_str / 'json'
    if not date_dir.exists():
        return []

    papers = []
    for json_file in date_dir.glob('*.json'):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                paper = json.load(f)
                papers.append(paper)
        except Exception as e:
            print(f"Error loading {json_file}: {e}")
            continue

    return papers


def get_paper_paths(paper: dict, date_str: str) -> dict:
    """获取论文的PDF和Markdown文件路径"""
    title = paper.get('title', 'untitled')
    safe_title = ''.join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)
    safe_title = safe_title[:100]

    date_dir = Path(data_root) / date_str

    # PDF路径
    pdf_path = date_dir / 'pdf' / f'{safe_title}.pdf'
    # Markdown路径
    markdown_path = date_dir / 'markdown' / f'{safe_title}.md'
    # Content路径
    content_path = date_dir / 'content' / f'{safe_title}.txt'

    return {
        'pdf_path': str(pdf_path) if pdf_path.exists() else None,
        'markdown_path': str(markdown_path) if markdown_path.exists() else None,
        'content_path': str(content_path) if content_path.exists() else None,
    }


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Paper AI API",
        "version": "1.0.0",
        "api_prefix": api_prefix,
        "docs": f"{api_prefix}/docs" if api_prefix else "/docs"
    }


@api_router.get("/api/dates")
async def get_dates():
    """获取所有可用的论文日期"""
    dates = get_paper_dates()
    return {"dates": dates}


def load_content_from_file(content_path: Optional[str]) -> str:
    """从文件加载content内容"""
    if not content_path or not Path(content_path).exists():
        return ""
    try:
        with open(content_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return ""


def filter_paper_by_keyword(paper: dict, keyword_lower: str, date_str: str) -> bool:
    """检查论文是否匹配关键词（支持title, summary, llm_summary, content），忽略大小写"""
    # 辅助函数：安全地将值转换为小写字符串
    def safe_lower(value) -> str:
        if value is None:
            return ''
        return str(value).lower()
    
    # 检查标题和摘要（忽略大小写）
    title = safe_lower(paper.get('title'))
    summary = safe_lower(paper.get('summary'))
    if keyword_lower in title or keyword_lower in summary:
        return True
    
    # 检查llm_summary（忽略大小写）
    llm_summary = safe_lower(paper.get('llm_summary'))
    if llm_summary and keyword_lower in llm_summary:
        return True
    
    # 检查content（可能存储在JSON中或文件中，忽略大小写）
    content = safe_lower(paper.get('content'))
    if not content:
        # 尝试从文件加载（content_path应该已经在paper中）
        content_path = paper.get('content_path')
        if content_path:
            content_raw = load_content_from_file(content_path)
            content = safe_lower(content_raw)
    
    if content and keyword_lower in content:
        return True
    
    return False


@api_router.get("/api/papers")
async def get_papers(
    date: Optional[str] = Query(None, description="日期筛选，格式：YYYY-MM-DD，为空时查询所有日期"),
    category: Optional[str] = Query(None, description="分类筛选，如：cs.CV"),
    keyword: Optional[str] = Query(None, description="关键词搜索（标题、摘要、llm_summary或content）"),
    author: Optional[str] = Query(None, description="作者筛选"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """
    获取论文列表

    支持的筛选条件：
    - date: 按日期筛选（为空时查询所有日期）
    - category: 按分类筛选（如 cs.CV, cs.AI）
    - keyword: 按关键词搜索标题、摘要、llm_summary或content
    - author: 按作者筛选
    """
    # 如果没有指定日期，查询所有日期
    if not date:
        dates = get_paper_dates()
        all_papers = []
        for date_str in dates:
            papers = load_papers_from_date(date_str)
            for paper in papers:
                # 添加文件路径信息和日期信息
                paths = get_paper_paths(paper, date_str)
                paper.update(paths)
                paper['date'] = date_str
                all_papers.append(paper)
        papers = all_papers
    else:
        # 获取指定日期的论文
        papers = load_papers_from_date(date)
        if not papers:
            return {
                "total": 0,
                "papers": [],
                "date": date,
                "filters": {
                    "category": category,
                    "keyword": keyword,
                    "author": author
                }
            }
        
        # 添加文件路径信息
        for paper in papers:
            paths = get_paper_paths(paper, date)
            paper.update(paths)
            paper['date'] = date

    # 应用筛选条件
    filtered_papers = papers

    if category:
        filtered_papers = [
            p for p in filtered_papers
            if category in p.get('categories', [])
        ]

    if keyword:
        keyword_lower = keyword.lower()
        # 使用并发过滤提升效率
        date_str = date if date else None
        with ThreadPoolExecutor(max_workers=10) as executor:
            # 为每篇论文创建过滤任务
            future_to_paper = {
                executor.submit(filter_paper_by_keyword, p, keyword_lower, p.get('date', date_str or '')): p
                for p in filtered_papers
            }
            
            # 收集匹配的论文
            matched_papers = []
            for future in as_completed(future_to_paper):
                paper = future_to_paper[future]
                try:
                    if future.result():
                        matched_papers.append(paper)
                except Exception as e:
                    print(f"Error filtering paper {paper.get('title', 'unknown')}: {e}")
            
            filtered_papers = matched_papers

    if author:
        author_lower = author.lower()
        filtered_papers = [
            p for p in filtered_papers
            if any(author_lower in a.lower() for a in p.get('authors', []))
        ]

    total = len(filtered_papers)

    # 按发布时间排序（最新的在前）
    filtered_papers.sort(
        key=lambda x: x.get('published', ''),
        reverse=True
    )

    # 应用分页
    paginated_papers = filtered_papers[offset:offset + limit]

    return {
        "total": total,
        "papers": paginated_papers,
        "date": date if date else "all",
        "filters": {
            "category": category,
            "keyword": keyword,
            "author": author
        }
    }


@api_router.get("/api/papers/all")
async def get_all_papers(
    category: Optional[str] = Query(None, description="分类筛选"),
    keyword: Optional[str] = Query(None, description="关键词搜索（标题、摘要、llm_summary或content）"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    limit: int = Query(100, ge=1, le=500, description="返回数量限制")
):
    """
    获取所有日期的论文列表

    支持跨日期查询和筛选
    """
    dates = get_paper_dates()

    # 应用日期范围筛选
    if start_date:
        dates = [d for d in dates if d >= start_date]
    if end_date:
        dates = [d for d in dates if d <= end_date]

    all_papers = []
    for date_str in dates:
        papers = load_papers_from_date(date_str)
        for paper in papers:
            # 添加文件路径信息和日期信息
            paths = get_paper_paths(paper, date_str)
            paper.update(paths)
            paper['date'] = date_str
            all_papers.append(paper)

    # 应用筛选条件
    filtered_papers = all_papers

    if category:
        filtered_papers = [
            p for p in filtered_papers
            if category in p.get('categories', [])
        ]

    if keyword:
        keyword_lower = keyword.lower()
        # 使用并发过滤提升效率
        with ThreadPoolExecutor(max_workers=10) as executor:
            # 为每篇论文创建过滤任务
            future_to_paper = {
                executor.submit(filter_paper_by_keyword, p, keyword_lower, p.get('date', '')): p
                for p in filtered_papers
            }
            
            # 收集匹配的论文
            matched_papers = []
            for future in as_completed(future_to_paper):
                paper = future_to_paper[future]
                try:
                    if future.result():
                        matched_papers.append(paper)
                except Exception as e:
                    print(f"Error filtering paper {paper.get('title', 'unknown')}: {e}")
            
            filtered_papers = matched_papers

    total = len(filtered_papers)

    # 按发布时间排序（最新的在前）
    filtered_papers.sort(
        key=lambda x: x.get('published', ''),
        reverse=True
    )

    # 应用限制
    paginated_papers = filtered_papers[:limit]

    return {
        "total": total,
        "papers": paginated_papers,
        "filters": {
            "category": category,
            "keyword": keyword,
            "start_date": start_date,
            "end_date": end_date
        }
    }


@api_router.get("/api/paper/{paper_id}")
async def get_paper_detail(paper_id: str):
    """
    获取单篇论文的详细信息

    paper_id格式：日期_标题（URL编码）
    例如：2026-01-13_RAVEN%3A%20Erasing%20Invisible%20Watermarks
    """
    try:
        # 解析paper_id
        # 格式：YYYY-MM-DD_Title
        parts = paper_id.split('_', 1)
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Invalid paper_id format")

        date_str = parts[0]
        title_from_id = parts[1]

        # 加载该日期的所有论文
        papers = load_papers_from_date(date_str)

        # 查找匹配的论文
        paper = None
        for p in papers:
            title = p.get('title', '')
            safe_title = ''.join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)
            if safe_title == title_from_id or title == title_from_id.replace('_', ' '):
                paper = p
                break

        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")

        # 添加文件路径信息
        paths = get_paper_paths(paper, date_str)
        paper.update(paths)

        return paper

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@api_router.get("/api/paper/{paper_id}/pdf")
async def get_paper_pdf(paper_id: str):
    """
    获取论文PDF文件

    paper_id格式：YYYY-MM-DD_Title
    """
    try:
        # 解析paper_id
        parts = paper_id.split('_', 1)
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Invalid paper_id format")

        date_str = parts[0]
        title_from_id = parts[1]

        # 获取论文信息
        papers = load_papers_from_date(date_str)
        paper = None
        for p in papers:
            title = p.get('title', '')
            safe_title = ''.join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)
            if safe_title == title_from_id or title == title_from_id.replace('_', ' '):
                paper = p
                break

        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")

        # 获取PDF路径
        paths = get_paper_paths(paper, date_str)
        pdf_path = paths.get('pdf_path')

        if not pdf_path or not Path(pdf_path).exists():
            raise HTTPException(status_code=404, detail="PDF file not found")

        return FileResponse(
            path=pdf_path,
            media_type='application/pdf',
            filename=Path(pdf_path).name
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@api_router.get("/api/paper/{paper_id}/markdown")
async def get_paper_markdown(paper_id: str):
    """
    获取论文Markdown总结文件

    paper_id格式：YYYY-MM-DD_Title
    """
    try:
        # 解析paper_id
        parts = paper_id.split('_', 1)
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Invalid paper_id format")

        date_str = parts[0]
        title_from_id = parts[1]

        # 获取论文信息
        papers = load_papers_from_date(date_str)
        paper = None
        for p in papers:
            title = p.get('title', '')
            safe_title = ''.join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)
            if safe_title == title_from_id or title == title_from_id.replace('_', ' '):
                paper = p
                break

        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")

        # 获取Markdown路径
        paths = get_paper_paths(paper, date_str)
        markdown_path = paths.get('markdown_path')

        if not markdown_path or not Path(markdown_path).exists():
            raise HTTPException(status_code=404, detail="Markdown file not found")

        return FileResponse(
            path=markdown_path,
            media_type='text/markdown',
            filename=Path(markdown_path).name
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@api_router.get("/api/categories")
async def get_categories():
    """获取所有论文分类"""
    dates = get_paper_dates()
    categories = set()

    for date_str in dates:
        papers = load_papers_from_date(date_str)
        for paper in papers:
            paper_categories = paper.get('categories', [])
            categories.update(paper_categories)

    return {
        "categories": sorted(list(categories))
    }


@api_router.get("/api/stats")
async def get_stats():
    """获取统计数据"""
    dates = get_paper_dates()
    total_papers = 0
    category_count = {}

    for date_str in dates:
        papers = load_papers_from_date(date_str)
        total_papers += len(papers)

        for paper in papers:
            for cat in paper.get('categories', []):
                category_count[cat] = category_count.get(cat, 0) + 1

    return {
        "total_papers": total_papers,
        "total_dates": len(dates),
        "categories": category_count,
        "latest_date": dates[0] if dates else None
    }


@api_router.get("/api/stats/daily")
async def get_daily_stats():
    """获取每天论文数量的统计"""
    dates = get_paper_dates()
    daily_stats = []

    for date_str in dates:
        papers = load_papers_from_date(date_str)
        daily_stats.append({
            "date": date_str,
            "count": len(papers)
        })

    # 按日期排序（最新的在前）
    daily_stats.sort(key=lambda x: x['date'], reverse=True)

    return {
        "daily_stats": daily_stats,
        "total_dates": len(daily_stats),
        "total_papers": sum(stat['count'] for stat in daily_stats)
    }


# 将API路由器注册到应用
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
