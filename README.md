# Bittensor (TAO) Subnet Dashboard - wangye-ge

这是一个专为 Bittensor (TAO) 网络设计的链上数据监控和可视化面板。

## 部署命令

新机器首次安装只运行一次安装向导：

```bash
cd /opt/wangye-ge
bash scripts/install.sh
```

已安装机器后续升级不要再运行安装向导，使用升级脚本：

```bash
cd /opt/wangye-ge
bash scripts/upgrade.sh
```

## 核心功能

1.  **子网看板**: 实时显示 128 个子网的名称、Alpha 价格、注册成本。
2.  **多维排序**: 支持按 ID、EMA、1小时交易量、24小时交易量排序。
3.  **动态监测**: 
    *   实时监控新区块，捕获子网注册/注销事件。
    *   定期校验子网列表，确保数据同步。
    *   分析赛马机制 (Racing Mechanism)，识别淘汰风险。
4.  **数据分析**: 北京时间 TAO 质押/解质押 Alpha 全网数据。
5.  **系统管理**:
    *   API 池管理: 支持多个 Dwellir API Key，自定义频率限制 (Rate Limiting)。
    *   日志系统: 严格按北京时间只保留最近 48 小时运行日志。
    *   通知系统: 支持 Telegram Bot 推送。
6.  **部署与升级**:
    *   首次安装: 必须运行 `bash scripts/install.sh`，交互式设置网页端口、后端端口、网页管理员账号和密码。
    *   后续升级: 必须运行 `bash scripts/upgrade.sh`，不要重复运行安装向导，避免重置端口、账号和密码。

## 技术栈

-   **后端**: FastAPI (Python 3.10+)
-   **前端**: React (TypeScript) + Vanilla CSS
-   **数据库**: SQLite (用于配置和日志)
-   **监控**: Websocket (Dwellir WSS) + Periodic Polling
-   **进程管理**: PM2
