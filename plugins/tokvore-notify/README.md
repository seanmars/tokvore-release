# tokvore-notify

把 agent hook 事件原封不動轉發給 tokvore 的 `POST /hooks`, 由 tokvore
backend 解讀; 當事件代表「需要使用者回應 / 等待輸入」時, backend 會跳出通知,
讓你離開終端機也能點擊聚焦回該 session.

## 架構

```
hooks.json ─stdin─▶ bridge.py
                       │  讀事件 → 補上本程序 pid → 讀 port → 原封轉發 (不解析)
                       ▼  POST /hooks  { "client": "claude|codex", "hook": <原始事件 + pid> }
                    tokvore  POST /hooks
                       │  依 client 選 interpreter → 解讀 + 過濾 + 通知
                       ▼
                    in-app toast / events 面板
```

- 這個 plugin 可用於 Claude / Codex hook。hook 的事件型別與內容本來就因 agent
  而異, 所以呼叫 `bridge.py` 時用 `--client claude|codex` 標記來源; 未帶參數時
  預設為 `"claude"`。backend 以它選擇對應 interpreter; 未知/不支援的 client 會被拒
  (HTTP 400)。
- `bridge.py` **不做任何事件解析**: 讀 stdin 的 agent hook 事件,
  `json.loads` 驗證為合法 JSON 後包成 `{ client, hook }` envelope, 從
  `~/.config/tokvore/settings.json` 的 `apiPort` 取 port (讀不到則用預設 `6789`),
  然後 POST。所有錯誤靜默 (tokvore 沒開也不影響 Claude)。
- 唯一會「補上」的欄位是 `hook.pid` (本 bridge 程序的 pid, 原本沒有才補)。bridge
  是 agent 程序的子孫且共用 console, tokvore 由此 pid 往上找到所屬終端機/IDE 視窗,
  將 session 註冊為可點擊聚焦。Codex hook 不帶 pid 也無對應環境變數, 少了這個 Codex
  session 只能列出而無法聚焦; Claude 會忽略它 (改用自己的 session descriptor)。
- 「哪些事件要通知、文案怎麼組、標題取哪」全部移到 backend 的 interpreter,
  因此調整通知行為不必重裝 plugin, backend 也能拿完整 payload 做更多操作。

## 涵蓋事件

實際是否通知與文案由 backend interpreter 判斷, 兩個 client 的 hook 事件型別本就不同,
故訂閱範圍各自獨立:

**Claude** (`hooks/hooks.json`): Stop、Notification、PermissionRequest、PreToolUse
(`AskUserQuestion` / `ExitPlanMode`)。會通知: Stop、Notification 的 `idle_prompt` /
`elicitation_dialog`、上述 PreToolUse、PermissionRequest; 其餘 (含 Notification 的
`permission_prompt`, 由 PermissionRequest 負責) 不通知。

**Codex** (`codex-hooks/hooks.json`): 依官方 Codex hooks 全量訂閱
SessionStart、UserPromptSubmit、PreToolUse、PermissionRequest、PostToolUse、
PreCompact、PostCompact、SubagentStart、SubagentStop、Stop, 並全部原封轉發給
backend。通知時會帶上「相關問題」: Stop 顯示 agent 的 `last_assistant_message`
(最後一句, 通常就是問題/摘要), 為空才退回 "Awaiting your input"; PermissionRequest
顯示 `tool_name` 並在有 `tool_input.command` 時附上命令預覽。

## 安裝

需要本機有 [`uv`](https://docs.astral.sh/uv/)。

### 方式一 (推薦) — 一鍵 plugin 安裝

```
/plugin marketplace add seanmars/tokvore-release
/plugin install tokvore-notify@tokvore
```

裝完即生效, 不用編輯 settings.json。更新: 作者 bump `plugin.json` 的 version 後,
使用者 `/plugin marketplace update`。

本機開發測試 (不經 marketplace):

```
claude --plugin-dir ./plugins/tokvore-notify
```

### 方式二 — 手動接進 `~/.claude/settings.json`

把 `hooks/hooks.json` 的條目複製進去, 並把 `${CLAUDE_PLUGIN_ROOT}` 換成
`plugins/tokvore-notify` 的絕對路徑, 例如:

```json
{
  "hooks": {
    "Stop": [{ "hooks": [{ "type": "command", "command": "uv run D:/workspace/seanmars/tokvore-release/plugins/tokvore-notify/scripts/bridge.py" }] }]
  }
}
```

(其餘 Notification / PermissionRequest / PreToolUse 比照, PreToolUse 加
`"matcher": "AskUserQuestion|ExitPlanMode"`。Codex hook 請在 command 後加
`--client codex`。)

## 自我測試

```
uv run plugins/tokvore-notify/scripts/bridge.py --selftest
```
