# tokvore-notify

把 agent hook 事件原封不動轉發給 tokvore 的 `POST /hooks`, 由 tokvore
backend 解讀; 當事件代表「需要使用者回應 / 等待輸入」時, backend 會跳出通知,
讓你離開終端機也能點擊聚焦回該 session.

## 架構

```
hooks.json ─stdin─▶ bridge.py
                       │  讀事件 → 讀 port → 原封轉發 (不解析)
                       ▼  POST /hooks  { "client": "claude|codex", "hook": <原始事件> }
                    tokvore  POST /hooks
                       │  依 client 選 interpreter → 解讀 + 過濾 + 通知
                       ▼
                    in-app toast / events 面板
```

- 這個 plugin 可用於 Claude / Codex hook。hook 的事件型別與內容本來就因 agent
  而異, 所以呼叫 `bridge.py` 時用 `--client claude|codex` 標記來源; 未帶參數時
  預設為 `"claude"`。backend 以它選擇對應 interpreter; 未知/不支援的 client 會被拒
  (HTTP 400)。
- `bridge.py` 只做一件事且**不做任何解析**: 讀 stdin 的 agent hook 事件,
  `json.loads` 驗證為合法 JSON 後包成 `{ client, hook }` envelope, 從
  `~/.config/tokvore/settings.json` 的 `apiPort` 取 port (讀不到則用預設 `6789`),
  然後 POST。所有錯誤靜默 (tokvore 沒開也不影響 Claude)。
- 「哪些事件要通知、文案怎麼組、標題取哪」全部移到 backend 的 interpreter,
  因此調整通知行為不必重裝 plugin, backend 也能拿完整 payload 做更多操作。

## 涵蓋事件 (只收「等待輸入」類)

訂閱維持窄的範圍 (見 `hooks/hooks.json`): Stop、Notification、PermissionRequest、
PreToolUse (`AskUserQuestion` / `ExitPlanMode`)。實際是否通知由 backend 判斷:
Stop、Notification 的 `idle_prompt` / `elicitation_dialog`、上述 PreToolUse、
PermissionRequest 會通知; 其餘 (含 Notification 的 `permission_prompt`, 由
PermissionRequest 負責) 不通知。

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
