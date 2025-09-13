"""
VibeGit 存储管理模块

该模块提供了用于管理用户与AI助手对话会话和轮次的存储功能。
它负责创建、存储和维护对话记录的文件系统结构。
"""

import json
import os
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# 数据模式版本号，用于向后兼容性检查
SCHEMA_VERSION = "1.0"


class VibeStore:
    """
    VibeGit 对话存储管理器
    
    该类负责管理用户与AI助手的对话会话(session)和对话轮次(round)。
    它维护一个基于文件系统的存储结构，支持会话管理、对话记录存储和检索。
    
    文件结构:
    - .vibe/
      - sessions/     # 会话文件目录
      - rounds/       # 对话轮次文件目录（按月份组织）
      - tmp/          # 临时文件目录
      - index.jsonl   # 索引文件
      - meta.json     # 元数据文件
    """
    
    def __init__(self, root_dir: str):
        """
        初始化 VibeStore 实例
        
        Args:
            root_dir (str): 项目根目录路径
        """
        self.root_dir = Path(root_dir)  # 项目根目录
        self.vibe_dir = self.root_dir / '.vibe'  # 存储目录
        self.rounds_dir = self.vibe_dir / 'rounds'  # 对话轮次存储目录
        self.sessions_dir = self.vibe_dir / 'sessions'  # 会话存储目录
        self.tmp_dir = self.vibe_dir / 'tmp'  # 临时文件目录
        self.index_file = self.vibe_dir / 'index.jsonl'  # 索引文件
        self.meta_file = self.vibe_dir / 'meta.json'  # 元数据文件
        self.active_session = None  # 当前活跃会话信息字典
        
        # 从环境变量获取会话超时时间，默认30分钟
        timeout_min = int(os.environ.get('VIBE_SESSION_TIMEOUT_MINUTES', '30') or '30')
        self.session_timeout_ms = timeout_min * 60 * 1000  # 转换为毫秒
        
        self.max_events_per_round = 200  # 每个对话轮次最大事件数
        self.rounds: Dict[str, Dict[str, Any]] = {}  # 内存中的对话轮次缓存

    def _now_iso(self) -> str:
        """
        获取当前时间的ISO格式字符串
        
        Returns:
            str: ISO格式的UTC时间字符串，精确到毫秒，格式如 "2025-09-12T10:30:45.123Z"
        """
        return datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'

    def _gen_id(self, prefix: str) -> str:
        """
        生成带前缀的唯一标识符
        
        Args:
            prefix (str): ID前缀，如 "sess"、"round" 等
            
        Returns:
            str: 格式为 "{prefix}-{timestamp}-{random}" 的唯一ID
                 例如: "sess-20250912T103045Z-a1b2"
        """
        ts = datetime.utcnow().strftime('%Y%m%dT%H%M%S') + 'Z'
        rand = os.urandom(3).hex()[:4]  # 生成4位随机十六进制字符串
        return f"{prefix}-{ts}-{rand}"

    def init(self):
        """
        初始化存储系统
        
        创建必要的目录结构，初始化元数据文件，并恢复或创建活跃会话。
        这个方法应该在使用存储系统之前调用。
        """
        # 创建所有必要的目录
        self.vibe_dir.mkdir(parents=True, exist_ok=True)
        self.rounds_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建元数据文件（如果不存在）
        if not self.meta_file.exists():
            self.meta_file.write_text(json.dumps({
                "schema_version": SCHEMA_VERSION,
                "privacy_note": "Phase1-no-sanitization"
            }, ensure_ascii=False, indent=2))
        
        # 尝试恢复最新的活跃会话
        sessions = list(self.sessions_dir.glob('sess-*.json'))
        if sessions:
            # 找到最新修改的会话文件
            latest = max(sessions, key=lambda p: p.stat().st_mtime)
            try:
                data = json.loads(latest.read_text(encoding='utf-8'))
                # 只有未结束的会话才能恢复为活跃会话
                if not data.get('ended_at'):
                    self.active_session = {
                        'session_id': data['session_id'],
                        'started_at': data['started_at'],
                        'last_activity': time.time() * 1000
                    }
            except Exception:
                pass  # 如果读取或解析失败，忽略并创建新会话
        
        # 如果没有活跃会话，创建新的
        if not self.active_session:
            self._create_new_session()
        else:
            print(f"[vibegit] restored active session {self.active_session['session_id']}")

    def _create_new_session(self, hint: str = None) -> str:
        """
        创建新的对话会话
        
        Args:
            hint (str, optional): 会话提示信息，用于标识会话创建的原因或上下文
            
        Returns:
            str: 新创建的会话ID
        """
        session_id = self._gen_id('sess')
        started_at = self._now_iso()
        
        # 更新内存中的活跃会话信息
        self.active_session = {
            'session_id': session_id,
            'started_at': started_at,
            'last_activity': time.time() * 1000
        }
        
        # 创建会话数据对象
        obj = {
            'schema_version': SCHEMA_VERSION,
            'session_id': session_id,
            'started_at': started_at,
            'ended_at': None,  # 新会话未结束
            'round_ids': [],   # 该会话包含的对话轮次ID列表
            'stats': { 'round_count': 0, 'events': 0 },  # 统计信息
            'hint': hint       # 会话提示信息
        }
        
        # 将会话信息写入文件
        (self.sessions_dir / f"{session_id}.json").write_text(
            json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8'
        )
        print(f"[vibegit] new session created: {session_id}")
        return session_id

    def maybe_rotate_session(self):
        """
        检查并可能轮换会话
        
        如果当前活跃会话超过超时时间（默认30分钟），则结束当前会话并创建新会话。
        这有助于保持会话的时间相关性和组织性。
        """
        if not self.active_session:
            return
            
        # 检查会话是否超时
        if (time.time() * 1000) - self.active_session['last_activity'] > self.session_timeout_ms:
            # 结束旧会话
            file = self.sessions_dir / f"{self.active_session['session_id']}.json"
            try:
                data = json.loads(file.read_text(encoding='utf-8'))
                data['ended_at'] = self._now_iso()  # 设置结束时间
                file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            except Exception:
                pass  # 如果更新失败，继续创建新会话
            
            # 创建新会话
            self._create_new_session()

    def start_round(self, session_id: str = None, session_hint: str = None) -> Dict[str, str]:
        """
        开始新的对话轮次
        
        Args:
            session_id (str, optional): 指定的会话ID。如果为None，使用当前活跃会话
            session_hint (str, optional): 会话提示信息，在需要创建新会话时使用
            
        Returns:
            Dict[str, str]: 包含 round_id、session_id 和 started_at 的字典
        """
        # 如果指定了会话ID，尝试使用该会话
        if session_id:
            file = self.sessions_dir / f"{session_id}.json"
            if file.exists():
                try:
                    data = json.loads(file.read_text(encoding='utf-8'))
                    # 如果会话已结束，创建新会话
                    if data.get('ended_at'):
                        session_id = self._create_new_session(session_hint)
                    else:
                        # 恢复指定的会话为活跃会话
                        self.active_session = {
                            'session_id': data['session_id'],
                            'started_at': data['started_at'],
                            'last_activity': time.time() * 1000
                        }
                except Exception:
                    # 如果读取或解析会话文件失败，使用当前活跃会话或创建新会话
                    session_id = self.active_session['session_id'] if self.active_session else self._create_new_session(session_hint)
            else:
                # 会话文件不存在，使用当前活跃会话或创建新会话
                session_id = self.active_session['session_id'] if self.active_session else self._create_new_session(session_hint)
        else:
            # 未指定会话ID，检查当前会话是否需要轮换，然后使用活跃会话
            self.maybe_rotate_session()
            session_id = self.active_session['session_id']
        # 创建新的对话轮次
        round_id = self._gen_id('round')
        started_at = self._now_iso()
        
        # 在内存中存储轮次信息
        self.rounds[round_id] = {
            'session_id': session_id,
            'started_at': started_at,
            'events': [],        # 该轮次的事件列表
            'closed': False      # 轮次是否已关闭
        }
        
        # 更新活跃会话的最后活动时间
        self.active_session['last_activity'] = time.time() * 1000
        print(f"[vibegit] start round {round_id} (session {session_id})")
        
        return { 'round_id': round_id, 'session_id': session_id, 'started_at': started_at }

    def _round_or_throw(self, round_id: str) -> Dict[str, Any]:
        """
        获取指定的对话轮次，如果不存在或已关闭则抛出异常
        
        Args:
            round_id (str): 对话轮次ID
            
        Returns:
            Dict[str, Any]: 对话轮次数据
            
        Raises:
            ValueError: 当轮次不存在时抛出 'ROUND_NOT_FOUND'
            ValueError: 当轮次已关闭时抛出 'ROUND_CLOSED'
        """
        r = self.rounds.get(round_id)
        if not r:
            raise ValueError('ROUND_NOT_FOUND')
        if r.get('closed'):
            raise ValueError('ROUND_CLOSED')
        return r

    def append_event(self, round_id: str, ev: Dict[str, Any]):
        """
        向指定的对话轮次追加事件
        
        Args:
            round_id (str): 对话轮次ID
            ev (Dict[str, Any]): 要追加的事件数据，应包含 'type' 字段
            
        Raises:
            ValueError: 当轮次不存在、已关闭或事件数量超限时抛出异常
        """
        r = self._round_or_throw(round_id)
        
        # 检查事件数量限制
        if len(r['events']) >= self.max_events_per_round:
            raise ValueError('ROUND_TOO_LARGE')
            
        r['events'].append(ev)
        
        # 对用户消息和助手消息进行日志记录
        if ev.get('type') in ('user_message','assistant_message'):
            snippet = (ev.get('content','') or '')[:40]
            print(f"[vibegit] {ev['type']} appended {round_id} ({snippet}...)")

    def end_round(self, round_id: str, status: str = 'ok') -> str:
        """
        结束指定的对话轮次并将其保存到文件
        
        Args:
            round_id (str): 要结束的对话轮次ID
            status (str, optional): 轮次结束状态，默认为 'ok'
            
        Returns:
            str: 保存的文件路径
            
        Raises:
            ValueError: 当轮次不存在或已关闭时抛出异常
        """
        r = self._round_or_throw(round_id)
        r['closed'] = True  # 标记轮次为已关闭
        ended_at = self._now_iso()
        
        # 根据开始时间创建月份目录（按年月组织：YYYY-MM）
        month_dir = self.rounds_dir / r['started_at'][:7]
        month_dir.mkdir(parents=True, exist_ok=True)
        file_path = month_dir / f"{round_id}.json"
        
        # 统计各类型事件的数量
        stats = {}
        for e in r['events']:
            stats[e['type']] = stats.get(e['type'], 0) + 1
        
        # 构建输出数据对象
        out = {
            'schema_version': SCHEMA_VERSION,
            'round_id': round_id,
            'session_id': r['session_id'],
            'started_at': r['started_at'],
            'ended_at': ended_at,
            'status': status,
            'events': [ dict(seq=i+1, **e) for i, e in enumerate(r['events']) ],  # 为事件添加序号
            'stats': stats
        }
        
        # 将轮次数据写入文件
        file_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
        
        # 更新对应的会话文件，添加该轮次ID和统计信息
        session_file = self.sessions_dir / f"{r['session_id']}.json"
        try:
            data = json.loads(session_file.read_text(encoding='utf-8'))
            data['round_ids'].append(round_id)          # 添加轮次ID到会话记录
            data['stats']['round_count'] += 1           # 增加轮次计数
            data['stats']['events'] += len(r['events']) # 增加事件计数
            session_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception:
            pass  # 如果更新会话文件失败，继续执行（不影响轮次保存）
        
        # 计算相对路径用于索引
        rel_path = file_path.relative_to(self.root_dir).as_posix()
        
        # 向索引文件追加轮次记录（用于快速查找和统计）
        with self.index_file.open('a', encoding='utf-8') as f:
            f.write(json.dumps({
                'round_id': round_id,
                'session_id': r['session_id'],
                'started_at': r['started_at'],
                'ended_at': ended_at,
                'path': rel_path,
                'counts': { 'events': len(r['events']) }
            }, ensure_ascii=False) + '\n')
        
        print(f"[vibegit] end round {round_id} -> {rel_path}")
        return str(file_path)
