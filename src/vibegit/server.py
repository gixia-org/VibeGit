"""
VibeGit MCP Server - 用于记录和跟踪AI助手与用户对话的MCP服务器

该服务器提供了一个log_round工具，用于记录完整的对话轮次，包括：
- 用户消息
- 助手回复
- 文件操作记录
- 工具调用记录
- 会话管理

主要功能：
1. 记录每个对话轮次的详细信息
2. 支持会话管理和持久化
3. 提供结构化的事件记录
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from mcp.server import FastMCP

from .store import VibeStore


# 在Windows上强制stdout使用UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 创建FastMCP服务器实例，名称为"vibegit-mcp"
# FastMCP是MCP协议的快速实现，用于构建工具服务器
app = FastMCP(name="vibegit-mcp")

# 创建存储实例，使用当前目录作为工作目录
# VibeStore负责管理会话数据、轮次记录和文件持久化
store = VibeStore('.')


@app.tool()
def log_round(
    user_message: str,
    assistant_messages: List[str],
    session_id: Optional[str] = None,
    session_hint: Optional[str] = None,
    file_views: Optional[List[str]] = None,
    file_writes: Optional[List[str]] = None,
    tool_calls: Optional[List[Dict[str, Any]]] = None,
    status: str = "ok",
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    REQUIRED: Record an entire user→assistant conversation round. MUST BE CALLED after every assistant response.
    
    CRITICAL WORKFLOW: You MUST call this tool as your FINAL action in every response to the user:
    1. Complete all your work (file operations, analysis, etc.)
    2. Provide your complete response to the user
    3. Call log_round as the LAST tool call
    4. DO NOT add any text after calling log_round
    
    This tool call marks the END of your response and returns control to the user.
    It represents a complete conversation round with clear boundaries.
    
    Usage: As your final action, call log_round with:
    - user_message: The original user input text (required)
    - assistant_messages: Array containing your complete response (required, minimum 1 item)
    - file_views: List of file paths you read/viewed (optional)
    - file_writes: List of file paths you created/modified (optional) 
    - tool_calls: List of tools you used with format [{"name": "tool_name", "args_summary": "brief description"}] (optional)
    - status: "ok" for successful completion or "aborted" for errors (default: "ok")
    - session_id: Existing session identifier if continuing a session (optional)
    - session_hint: Hint for new session creation (optional)
    - meta: Additional metadata like model info, tokens used, etc. (optional)
    
    IMPORTANT: 
    - Call this tool ONCE per user interaction as your FINAL tool call
    - Include all your response parts in assistant_messages array if delivered in chunks
    - No text should follow this tool call - it signals response completion
    """
    # 第一步：验证和规范化输入参数
    # 确保所有必需参数存在且格式正确，处理可选参数的默认值
    validated_data = _validate_log_round({
        'user_message': user_message,
        'assistant_messages': assistant_messages,
        'session_id': session_id,
        'session_hint': session_hint,
        'file_views': file_views or [],  # 如果为None则使用空列表
        'file_writes': file_writes or [],
        'tool_calls': tool_calls or [],
        'status': status,
        'meta': meta or {}
    })
    
    # 第二步：执行实际的日志记录业务逻辑
    # 创建轮次记录，生成事件序列，保存到存储系统
    result = _handle_log_round(validated_data)
    return result


def _validate_log_round(args: dict) -> dict:
    """
    【输入验证函数】验证和规范化log_round的输入参数
    
    该函数负责：
    1. 检查必需参数是否存在且有效
    2. 限制文本长度防止过大数据
    3. 规范化和清理输入数据
    4. 返回验证后的数据字典
    
    参数：
    - args: 包含所有输入参数的字典
    
    返回：
    - 验证和规范化后的数据字典
    
    异常：
    - ValueError: 当输入参数不符合要求时抛出验证错误
    """
    # 验证必需字段：用户消息
    if 'user_message' not in args or not isinstance(args['user_message'], str) or not args['user_message'].strip():
        raise ValueError('VALIDATION_ERROR: user_message required non-empty string')
    
    # 验证必需字段：助手回复消息数组
    if 'assistant_messages' not in args or not isinstance(args['assistant_messages'], list) or not args['assistant_messages']:
        raise ValueError('VALIDATION_ERROR: assistant_messages must be non-empty array')
    
    # 处理用户消息长度限制（最大20,000字符）
    user_msg = args['user_message'].strip()
    if len(user_msg) > 20000:
        user_msg = user_msg[:20000]  # 截断过长的消息
    
    # 处理助手回复消息数组，每条消息最大30,000字符
    assistants = []
    for i, m in enumerate(args['assistant_messages']):
        if not isinstance(m, str) or not m.strip():
            raise ValueError(f'VALIDATION_ERROR: assistant_messages[{i}] empty')
        txt = m.strip()
        if len(txt) > 30000:
            txt = txt[:30000]  # 截断过长的消息
        assistants.append(txt)
    
    def norm_str_list(key):
        """
        内部辅助函数：规范化字符串列表
        过滤掉空字符串，只保留有效的非空字符串
        """
        arr = args.get(key) or []
        if not isinstance(arr, list):
            raise ValueError(f'VALIDATION_ERROR: {key} must be array')
        norm = []
        for i, v in enumerate(arr):
            if not isinstance(v, str) or not v.strip():
                continue  # 跳过空字符串或非字符串项
            norm.append(v.strip())
        return norm
    
    # 规范化文件路径列表
    file_views = norm_str_list('file_views')
    file_writes = norm_str_list('file_writes')
    
    # 处理工具调用记录
    tool_calls_raw = args.get('tool_calls') or []
    if not isinstance(tool_calls_raw, list):
        raise ValueError('VALIDATION_ERROR: tool_calls must be array')
    
    tool_calls = []
    for i, tc in enumerate(tool_calls_raw):
        # 验证工具调用记录格式：必须包含name字段
        if not isinstance(tc, dict) or 'name' not in tc or not isinstance(tc['name'], str) or not tc['name'].strip():
            raise ValueError(f'VALIDATION_ERROR: tool_calls[{i}] invalid')
        entry = {'name': tc['name'].strip()}
        # 可选的参数摘要字段，限制长度为500字符
        if 'args_summary' in tc and isinstance(tc['args_summary'], str):
            entry['args_summary'] = tc['args_summary'][:500]
        tool_calls.append(entry)
    
    # 验证状态字段：只允许'ok'或'aborted'
    status = args.get('status', 'ok')
    if status not in ('ok', 'aborted'):
        raise ValueError('VALIDATION_ERROR: status invalid')
    
    # 处理可选字段，确保类型正确
    session_id = args.get('session_id') if isinstance(args.get('session_id'), str) else None
    session_hint = args.get('session_hint') if isinstance(args.get('session_hint'), str) else None
    meta = args.get('meta') if isinstance(args.get('meta'), dict) else {}
    
    # 计算总事件数量，防止单轮次事件过多（限制200个事件）
    # 事件包括：1个用户消息 + 助手消息数 + 文件查看数 + 文件写入数 + 工具调用数
    total_events = 1 + len(assistants) + len(file_views) + len(file_writes) + len(tool_calls)
    if total_events > 200:
        raise ValueError('VALIDATION_ERROR: too many events in one round')
    
    # 返回验证和规范化后的数据
    return {
        'user_message': user_msg,
        'assistant_messages': assistants,
        'file_views': file_views,
        'file_writes': file_writes,
        'tool_calls': tool_calls,
        'status': status,
        'session_id': session_id,
        'session_hint': session_hint,
        'meta': meta,
        'total_events': total_events
    }

def _handle_log_round(data: dict):
    """
    【业务逻辑处理函数】处理log_round的核心业务逻辑
    
    该函数负责：
    1. 创建或获取对话轮次
    2. 生成时间戳序列的事件记录
    3. 保存各类事件到存储系统
    4. 结束轮次并返回结果
    
    参数：
    - data: 已验证的数据字典
    
    返回：
    - 包含轮次信息和保存结果的字典
    """
    # 第一步：开始新的对话轮次
    # store.start_round会创建新轮次或继续现有会话
    round_info = store.start_round(data['session_id'], data['session_hint'])
    round_id = round_info['round_id']
    
    # 第二步：准备事件时间戳生成器
    # 使用当前UTC时间作为基准，为每个事件生成递增的时间戳
    base_time = datetime.utcnow()
    seq_delta = 0  # 毫秒增量，确保事件时间戳的顺序性
    
    def next_ts():
        """生成下一个事件的时间戳"""
        nonlocal seq_delta
        t = (base_time + timedelta(milliseconds=seq_delta)).isoformat(timespec='milliseconds') + 'Z'
        seq_delta += 1  # 每次调用递增1毫秒，确保时间戳唯一且有序
        return t
    
    # 第三步：记录用户消息事件
    # 每个轮次的第一个事件总是用户的输入消息
    store.append_event(round_id, {
        'ts': next_ts(),
        'type': 'user_message',
        'content': data['user_message'],
        'meta': data['meta']  # 包含模型信息、token使用量等元数据
    })
    
    # 第四步：记录助手回复消息事件
    # 如果助手的回复被分成多个部分，每个部分都会被记录为单独的事件
    for msg in data['assistant_messages']:
        store.append_event(round_id, {
            'ts': next_ts(),
            'type': 'assistant_message',
            'content': msg
        })
    
    # 第五步：记录文件查看事件
    # 记录助手在此轮次中读取或查看的所有文件路径
    for path in data['file_views']:
        store.append_event(round_id, {
            'ts': next_ts(),
            'type': 'file_view',
            'path': path
        })
    
    # 第六步：记录文件写入事件
    # 记录助手在此轮次中创建或修改的所有文件路径
    for path in data['file_writes']:
        store.append_event(round_id, {
            'ts': next_ts(),
            'type': 'file_write',
            'type': 'file_write',
            'path': path
        })
    
    # 第七步：记录工具调用事件
    # 记录助手在此轮次中使用的所有工具及其参数摘要
    for tc in data['tool_calls']:
        ev = {
            'ts': next_ts(),
            'type': 'tool_call',
            'name': tc['name']  # 工具名称（必需）
        }
        # 如果有参数摘要，也一并记录
        if 'args_summary' in tc:
            ev['args_summary'] = tc['args_summary']
        store.append_event(round_id, ev)
    
    # 第八步：结束轮次并保存到文件
    # store.end_round会将所有事件数据持久化到JSON文件
    saved = store.end_round(round_id, data['status'])
    
    # 第九步：返回操作结果
    return {
        'round_id': round_id,                    # 本轮次的唯一标识符
        'session_id': round_info['session_id'], # 会话的唯一标识符
        'events_recorded': data['total_events'], # 本轮次记录的事件总数
        'saved_file': saved                      # 保存数据的文件路径
    }


def main():
    """
    【主入口函数】启动VibeGit MCP服务器
    
    该函数负责：
    1. 初始化存储系统（创建必要的目录结构）
    2. 启动MCP服务器，监听stdio传输协议
    
    当服务器启动后，它会等待MCP客户端的连接和工具调用请求。
    """
    # 初始化存储系统
    # 这会创建必要的目录结构，如.vibe/sessions/和.vibe/rounds/
    store.init()
    
    # 启动MCP服务器
    # 使用stdio传输协议，这意味着服务器通过标准输入/输出与客户端通信
    # 这是MCP协议的标准通信方式，适合与Claude等AI助手集成
    app.run(transport='stdio')


if __name__ == '__main__':
    # 当脚本直接运行时（而不是被导入时），启动服务器
    main()