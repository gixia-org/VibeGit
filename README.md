# VibeGit / 筑基计划

记录 Vibe Coding 交互历史（prompt / response / 行为事件）的最小可行方案实验仓库。采用 MCP Server（原型）方式验证：无需替换现有 AI 插件，通过工具调用将对话轮次写入项目内 `.vibe/` 目录。

## 核心想法概述
- 传统 Git 仅追踪代码 diff，而在 AI 辅助开发中，对话本身是过程资产。
- 通过 MCP Server 暴露记录接口，模型或客户端在生成 / 浏览 / 写入操作发生时调用，生成结构化日志。
- 早期不绑定 Git 提交与 diff，聚焦“能否稳定拿到对话轮 + 基本事件”。

## Phase 1 范围 (MVP)
实现：
- Session & Round 概念（Round = 单次用户提问到结束的一组事件；Session = 多个 Round 的连续集合）。
- 事件类型：user_message / assistant_message / file_view / file_write / tool_call。
- 逐事件即时写入内存，Round 结束落盘。
- `.vibe/` 目录结构（按月分片 rounds、sessions 元文件、索引）。
- Session 自动超时（默认 30 分钟无活动新建）。

不包含：接受代码判断、diff、运行命令、隐私脱敏、Git 绑定、回放 UI。

## 目录结构
```
.vibe/
  rounds/<YYYY-MM>/round-*.json
  sessions/sess-*.json
  index.jsonl
  meta.json
```

## 安装与运行
进入 `server/`：
```powershell
cd server
npm install
npm start
```
可选环境变量：
- `VIBE_SESSION_TIMEOUT_MINUTES` (默认 30)

示例：
```powershell
$env:VIBE_SESSION_TIMEOUT_MINUTES=15
npm start
```

启动后进程监听 stdin（JSON-RPC 行协议）。日志会输出 session/round 创建与关键消息事件。

## JSON-RPC 调用示例
在运行的进程控制台中逐行粘贴（或使用其他管道方式）。真实 MCP 客户端会发送 `initialize` → `tools/list` → 多次 `tools/call`：
```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"clientInfo":{"name":"manual","version":"0"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"start_round","arguments":{}}}
```
响应示例：
```json
{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"0.1","serverInfo":{"name":"vibegit-mcp","version":"0.1.0"},"capabilities":{"tools":{}}}}
{"jsonrpc":"2.0","id":2,"result":{"tools":[{"name":"start_round"...}]}}
{"jsonrpc":"2.0","id":3,"result":{"content":[{"type":"json","json":{"round_id":"round-...","session_id":"sess-...","started_at":"..."}}]}}
```
使用返回的 round_id 继续事件（工具调用统一用 `tools/call`）：
```json
{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"log_user_message","arguments":{"round_id":"<ROUND_ID>","content":"请帮我写一个排序"}}}
{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"log_assistant_message","arguments":{"round_id":"<ROUND_ID>","content":"这里是思路..."}}}
{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"log_file_view","arguments":{"round_id":"<ROUND_ID>","path":"src/sort.py"}}}
{"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"name":"log_file_write","arguments":{"round_id":"<ROUND_ID>","path":"src/sort.py"}}}
{"jsonrpc":"2.0","id":8,"method":"tools/call","params":{"name":"log_tool_call","arguments":{"round_id":"<ROUND_ID>","name":"explain_complexity"}}}
{"jsonrpc":"2.0","id":9,"method":"tools/call","params":{"name":"end_round","arguments":{"round_id":"<ROUND_ID>"}}}
```

完成后查看：
```
.vibe/index.jsonl
.vibe/rounds/<YYYY-MM>/round-*.json
.vibe/sessions/sess-*.json
```
`index.jsonl` 中 `path` 字段为相对项目根路径。

## 常见问题
1. 未调用 end_round：该 round 不会落盘（Phase 1 不做恢复）。
2. 事件超限：超过 200 事件返回错误 `ROUND_TOO_LARGE`。
3. Session 何时切换？超时（默认 30 分钟）后下一个 start_round 自动新建。
4. 支持批量事件吗？当前不支持，未来可增加 `log_events_batch`。
5. 真实 MCP 客户端能直接用吗？是的，需按 `initialize` → `tools/list` → `tools/call` 模式交互；未来若协议更新可同步调整。

## 下一步方向（非本阶段）
- 部分事件提前落盘 / partial 文件恢复
- 批量接口 & 性能测试
- Git commit 关联 & diff 捕获
- Hash 链 / 防篡改 / 签名
- 回放 UI & 时间轴
- 隐私过滤与策略配置

## 许可证
暂未指定（后续补充）。

---
欢迎针对 Phase 1 结构和接口提出改进建议。
