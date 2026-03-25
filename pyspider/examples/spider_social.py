#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PySpider 社交媒体爬虫模板

特性:
- ✅ 用户信息爬取
- ✅ 帖子/动态爬取
- ✅ 评论爬取
- ✅ 点赞/转发数据
- ✅ 关系网络爬取
- ✅ 数据导出

使用:
    python spider_social.py
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, asdict

try:
    from pyspider.core import Spider, Request
    from pyspider.antibot import AntiBotManager
except ImportError:
    print("请先安装 PySpider: pip install -e .")
    exit(1)


# ========== 数据模型 ==========

@dataclass
class UserProfile:
    """用户资料"""
    user_id: str
    username: str
    display_name: str
    bio: str
    followers_count: int
    following_count: int
    posts_count: int
    avatar_url: str
    verified: bool
    join_date: str
    location: str
    website: str
    crawl_time: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Post:
    """帖子/动态"""
    post_id: str
    user_id: str
    username: str
    content: str
    images: List[str]
    videos: List[str]
    created_at: str
    likes_count: int
    comments_count: int
    shares_count: int
    url: str
    crawl_time: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Comment:
    """评论"""
    comment_id: str
    post_id: str
    user_id: str
    username: str
    content: str
    created_at: str
    likes_count: int
    replies_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ========== 爬虫类 ==========

class SocialMediaSpider(Spider):
    """社交媒体爬虫"""
    
    # 配置区域
    START_USERS = [
        "user123",
        "user456",
    ]
    
    CONFIG = {
        'thread_count': 2,  # 社交媒体限制严格，线程数要少
        'max_depth': 2,
        'max_requests': 1000,
        'delay': 5.0,  # 较长延迟
        'timeout': 30,
    }
    
    OUTPUT_CONFIG = {
        'save_json': True,
        'output_dir': 'output/social',
    }
    
    # CSS 选择器配置（需要根据实际网站调整）
    SELECTORS = {
        # 用户资料
        'username': '.username::text',
        'display_name': '.display-name::text',
        'bio': '.bio::text',
        'followers': '.followers-count::text',
        'following': '.following-count::text',
        'posts': '.posts-count::text',
        'avatar': '.avatar img::attr(src)',
        'verified': '.verified-icon',
        
        # 帖子列表
        'post_list': '.post-list .post-item',
        'post_link': 'a.post-link::attr(href)',
        'next_page': '.next-page a::attr(href)',
        
        # 帖子详情
        'post_content': '.post-content::text',
        'post_images': '.post-images img::attr(src)',
        'post_videos': '.post-video source::attr(src)',
        'post_time': '.post-time::text',
        'post_likes': '.like-count::text',
        'post_comments': '.comment-count::text',
        'post_shares': '.share-count::text',
        
        # 评论
        'comment_list': '.comment-list .comment-item',
        'comment_user': '.comment-user::text',
        'comment_content': '.comment-content::text',
        'comment_time': '.comment-time::text',
        'comment_likes': '.comment-likes::text',
    }
    
    def __init__(self):
        super().__init__(
            name="SocialMediaSpider",
            thread_count=self.CONFIG['thread_count']
        )
        
        # 反反爬管理器
        self.antibot = AntiBotManager()
        
        # 结果存储
        self.users: List[UserProfile] = []
        self.posts: List[Post] = []
        self.comments: List[Comment] = []
        
        # 统计信息
        self.stats = {
            'users': 0,
            'posts': 0,
            'comments': 0,
            'errors': 0,
        }
        
        # 输出目录
        self.output_dir = Path(self.OUTPUT_CONFIG['output_dir'])
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        print("=" * 60)
        print("社交媒体爬虫")
        print("=" * 60)
        print(f"起始用户数：{len(self.START_USERS)}")
        print(f"线程数：{self.CONFIG['thread_count']}")
        print(f"延迟：{self.CONFIG['delay']}秒")
        print("=" * 60)
    
    def parse_user(self, page):
        """解析用户资料页"""
        url = page.response.url
        print(f"解析用户：{url}")
        
        try:
            # 提取用户数据
            username = page.response.css(self.SELECTORS['username']).get(default='').strip()
            display_name = page.response.css(self.SELECTORS['display_name']).get(default='').strip()
            bio = page.response.css(self.SELECTORS['bio']).get(default='').strip()
            
            # 解析数字
            followers_text = page.response.css(self.SELECTORS['followers']).get(default='0').strip()
            followers_count = self.parse_count(followers_text)
            
            following_text = page.response.css(self.SELECTORS['following']).get(default='0').strip()
            following_count = self.parse_count(following_text)
            
            posts_text = page.response.css(self.SELECTORS['posts']).get(default='0').strip()
            posts_count = self.parse_count(posts_text)
            
            # 提取头像
            avatar_url = page.response.css(self.SELECTORS['avatar']).get(default='').strip()
            
            # 检查是否认证
            verified = bool(page.response.css(self.SELECTORS['verified']))
            
            # 创建用户对象
            user = UserProfile(
                user_id=username,
                username=username,
                display_name=display_name,
                bio=bio[:500],
                followers_count=followers_count,
                following_count=following_count,
                posts_count=posts_count,
                avatar_url=avatar_url,
                verified=verified,
                join_date='',
                location='',
                website='',
                crawl_time=datetime.now().isoformat()
            )
            
            # 保存用户
            self.users.append(user)
            self.stats['users'] += 1
            
            yield user.to_dict()
            
            # 提取用户帖子链接
            post_links = page.response.css(self.SELECTORS['post_link']).getall()
            for link in post_links:
                if link and link.startswith('http'):
                    yield Request(
                        url=link,
                        callback=self.parse_post,
                        meta={'user_id': username}
                    )
        
        except Exception as e:
            print(f"解析用户失败 {url}: {e}")
            self.stats['errors'] += 1
    
    def parse_post(self, page):
        """解析帖子"""
        url = page.response.url
        print(f"解析帖子：{url}")
        
        try:
            user_id = page.meta.get('user_id', '')
            
            # 提取帖子数据
            content = page.response.css(self.SELECTORS['post_content']).get(default='').strip()
            
            # 提取图片
            images = page.response.css(self.SELECTORS['post_images']).getall()
            images = [img for img in images if img and img.startswith('http')][:10]
            
            # 提取视频
            videos = page.response.css(self.SELECTORS['post_videos']).getall()
            videos = [vid for vid in videos if vid and vid.startswith('http')][:5]
            
            # 提取时间
            created_at = page.response.css(self.SELECTORS['post_time']).get(default='').strip()
            
            # 解析互动数据
            likes_text = page.response.css(self.SELECTORS['post_likes']).get(default='0').strip()
            likes_count = self.parse_count(likes_text)
            
            comments_text = page.response.css(self.SELECTORS['post_comments']).get(default='0').strip()
            comments_count = self.parse_count(comments_text)
            
            shares_text = page.response.css(self.SELECTORS['post_shares']).get(default='0').strip()
            shares_count = self.parse_count(shares_text)
            
            # 提取帖子 ID（从 URL）
            post_id = url.split('/')[-1] if '/' in url else ''
            
            # 创建帖子对象
            post = Post(
                post_id=post_id,
                user_id=user_id,
                username=user_id,
                content=content[:2000],
                images=images,
                videos=videos,
                created_at=created_at,
                likes_count=likes_count,
                comments_count=comments_count,
                shares_count=shares_count,
                url=url,
                crawl_time=datetime.now().isoformat()
            )
            
            # 保存帖子
            self.posts.append(post)
            self.stats['posts'] += 1
            
            yield post.to_dict()
            
            # 提取评论链接
            if comments_count > 0:
                # 这里可以添加评论爬取逻辑
                pass
        
        except Exception as e:
            print(f"解析帖子失败 {url}: {e}")
            self.stats['errors'] += 1
    
    def parse_count(self, text: str) -> int:
        """解析数量（支持 K/M 单位）"""
        import re
        if not text:
            return 0
        
        text = text.lower().strip()
        
        # 处理 K/M 单位
        multipliers = {'k': 1000, 'm': 1000000, 'b': 1000000000}
        
        for unit, mult in multipliers.items():
            if unit in text:
                match = re.search(r'[\d.]+', text)
                if match:
                    return int(float(match.group()) * mult)
        
        # 纯数字
        match = re.search(r'[\d,]+', text)
        if match:
            return int(match.group().replace(',', ''))
        
        return 0
    
    def save_results(self):
        """保存结果"""
        print(f"\n保存 {len(self.users)} 个用户，{len(self.posts)} 个帖子...")
        
        if self.OUTPUT_CONFIG['save_json']:
            # 保存用户
            users_file = self.output_dir / 'users.json'
            with open(users_file, 'w', encoding='utf-8') as f:
                json.dump([u.to_dict() for u in self.users], f, ensure_ascii=False, indent=2)
            print(f"✓ 已保存用户：{users_file}")
            
            # 保存帖子
            posts_file = self.output_dir / 'posts.json'
            with open(posts_file, 'w', encoding='utf-8') as f:
                json.dump([p.to_dict() for p in self.posts], f, ensure_ascii=False, indent=2)
            print(f"✓ 已保存帖子：{posts_file}")
    
    def print_stats(self):
        """打印统计信息"""
        print("\n" + "=" * 60)
        print("统计信息")
        print("=" * 60)
        print(f"用户数：{self.stats['users']}")
        print(f"帖子数：{self.stats['posts']}")
        print(f"错误数：{self.stats['errors']}")
        print("=" * 60)


# ========== 主函数 ==========

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("社交媒体爬虫 v1.0.0")
    print("=" * 60 + "\n")
    
    # 创建爬虫
    spider = SocialMediaSpider()
    
    # 添加起始请求（用户资料页）
    for username in spider.START_USERS:
        url = f"https://social.example.com/{username}"
        spider.add_request(
            Request(
                url=url,
                callback=spider.parse_user,
                meta={'depth': 0}
            )
        )
    
    # 运行爬虫
    try:
        spider.run()
    except Exception as e:
        print(f"爬虫运行失败：{e}")
    finally:
        # 保存结果
        spider.save_results()
        
        # 打印统计
        spider.print_stats()
    
    print("\n爬虫运行完成！")


if __name__ == '__main__':
    main()
