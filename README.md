# 拼词之星

拼词之星是一个面向英语单词学习的导入和词典补全系统。你可以上传 Excel 单词表，系统会先显示表格预览，再按你选择的行和列保存到 MySQL，并尽量补全音标、可朗读音频、英文定义、英文例句、图片和中文定义。

## 快速启动

1. 复制配置：

```powershell
Copy-Item .env.example .env
```

2. 启动 MySQL：

```powershell
docker compose up -d mysql
```

3. 安装依赖并启动应用：

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

4. 打开：

```text
http://127.0.0.1:8000
```

## 项目维护文档

- `PROJECT_STATUS.md`：当前目标、页面覆盖、验证和部署流程。
- `STYLE_GUIDE.md`：Vue 化后的全局样式入口和视觉规则。
- `VUE_MIGRATION_STATUS.md`：Vue 化迁移过程和历史拆分记录。

常用验证命令：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify-release.ps1
```

HTTP 冒烟检查的路径维护在 `scripts/verification-urls.json`。

## 本机 Ubuntu 虚拟机运行

本机开发环境部署在 Hyper-V 虚拟机 `QuantRadar-Ubuntu`
（`192.168.1.186`）中，不依赖生产服务器或线上 RDS。应用由 Ubuntu
systemd 服务 `speakeasy-local.service` 管理，监听局域网端口 `8011`；
MySQL 只接受虚拟机本机连接。

```powershell
# 启动 Ubuntu 中的 MySQL 和应用（会提示输入 qradmin 的 sudo 密码）
powershell -ExecutionPolicy Bypass -File scripts\local.ps1 start

# 从 Windows 检查 Ubuntu 服务状态
powershell -ExecutionPolicy Bypass -File scripts\local.ps1 status

# 停止 Ubuntu 中的应用和 MySQL（会提示输入 sudo 密码）
powershell -ExecutionPolicy Bypass -File scripts\local.ps1 stop
```

启动后打开 `http://192.168.1.186:8011/`。Ubuntu 上可用下面的命令查看日志：

```bash
journalctl -u speakeasy-local.service -f
```

只检查 Vue 页面/路由覆盖：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check-vue-coverage.ps1
```

生产发布会通过 SSH 密钥直接更新本地 Ubuntu 虚拟机
`192.168.1.186`，外网代理机 `139.224.9.235` 不存放应用代码：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\deploy-production.ps1
```

线上日志同样直接从 Ubuntu 的 systemd 服务读取：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check-production-logs.ps1
```

GitHub 自动发布使用内网 Ubuntu 上的独立 self-hosted Runner
`speakeasy-production`。推送到 `main` 或在 Actions 页面手动运行
`Deploy SpeakEasy production` 后，工作流会直接同步到
`/opt/speakeasy/current` 并重启 `speakeasy-local.service`。
`139.224.9.235` 仅转发公网请求，不运行 Runner，也不保存发布代码。

## 好词好句

本项目已合并 BookLearner，二级目录为 `好词好句`。启动同一个服务后打开：

```text
http://127.0.0.1:8000/好词好句
```

它可以按书名或作者模糊搜索，优先从公版全文提炼短句和难词；没有可分析全文时，只显示书籍元信息，不编造语录。

## Excel 格式

上传后会先进入预览页，你可以手动选择英文单词列、要导入的行、要导入的列。

推荐包含 `word` 或 `单词` 列。若没有这些列，系统会自动尝试识别最像英文单词的列，并跳过纯数字内容。

可选列：

- `phonetic` / `音标`
- `chinese_definition` / `中文定义`
- `note` / `备注`

## 词典数据源

详情页的“补全当前词”统一按以下顺序执行：

1. 先匹配 SPB 小程序词库并获取详情；当前所属组优先，普通词表也会匹配已下载的 SPB 目录。
2. 小程序未收录、接口暂不可用或仍有缺项时，再使用在线词典补全音标、词性、中英文定义、英文例句和英美发音。
3. 在线补全只填空缺，不覆盖已有的小程序内容或手动锁定字段；已有英文定义时，缺失的中文释义以该定义为准翻译。

资料已齐全时不会再查询在线词典。在线来源也无结果时保留已有内容，不编造缺失信息。

在线补全默认使用免费开放词典接口；不可用时尝试 Cambridge 在线词典：

```text
https://dictionaryapi.dev/
```

它可以返回英文定义、音标、例句和部分英式/美式发音音频。

韦氏词典是可选增强源。在 `.env` 中填写：

```env
MERRIAM_WEBSTER_API_KEY=你的韦氏API_KEY
```

未配置 Key 时，系统会自动使用免费开放词典，不会因为缺少韦氏 Key 导入失败。
