<div align="center">

# Tokvore

</div>

Tokvore 是常駐系統匣 (system tray) 的桌面應用, 用來管理散落在多個 terminal 與 IDE 視窗裡的 Agent session. 原始碼維持私有, 這個公開 repo 提供兩樣東西:

- **應用安裝檔** — 發佈在 [Releases](https://github.com/seanmars/tokvore-release/releases).
- **Claude Code hook plugin** (`tokvore-notify`) — 透過本 repo 的 marketplace 一鍵安裝, 讓 Claude Code 的「等待輸入」事件跳出可點擊聚焦的通知.

## 下載安裝應用

從 [Releases](https://github.com/seanmars/tokvore-release/releases) 下載最新的 `tokvore_x.y.z_x64-setup.exe`, 執行後即可安裝.

> [!NOTE]
> 安裝檔目前未經 OS 程式碼簽章, 首次執行時 Windows SmartScreen 可能顯示「不受信任」警告. 點「其他資訊」(More info) -> 「仍要執行」(Run anyway) 即可繼續.

安裝後應用程式會在啟動時自動於背景檢查更新, 也可在「Settings -> 版本與更新」手動檢查並一鍵下載安裝新版.

## 授權

[MIT License](./LICENSE).
