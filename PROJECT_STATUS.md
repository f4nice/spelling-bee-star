# SpeakEasy Project Status

这份文件是每轮开工前的项目总览。长期目标是：把 SpeakEasy 做成一个 Vue 化、稳定上线、样式统一美观、适合长期背单词和复盘错误的学习工具；每次修改都要本地验证、提交 Git、部署服务器，并把项目状态记录到 Markdown，减少重复全局扫描。

## 当前状态

- 线上地址：`http://47.116.28.2:8010/`
- 生产目录：`/opt/spelling-bee-star`
- 当前主分支：`main`
- 样式基线提交：`6f009f0 Polish global Vue styling`
- Vue 主应用：`frontend/src/app`
- 挑战页应用：`frontend/src/challenge`
- 全局样式入口：`app/static/styles.css`
- Vue 构建产物：`app/static/vue`
- HTML shell：`app/templates/vue_app.html`
- 验证脚本：`scripts/verify-release.ps1`
- 线上日志检查脚本：`scripts/check-production-logs.ps1`
- 生产部署脚本：`scripts/deploy-production.ps1`

## 页面覆盖

已由 Vue shell 承载的主要页面：

- `/`
- `/lists`
- `/lists/{word_list_id}`
- `/upload`
- `/upload/preview/{preview_id}`
- `/words/{word_id}`
- `/challenge/{word_list_id}`
- `/challenge-calendar/{day}`
- `/wrong-words`
- `/newspaper`
- `/newspaper/{section_key}/{article_index}`
- `/booklearner`
- `/booklearner/upload`
- `/booklearner/quotes`
- `/booklearner/detail/{analysis_id}`

相关 API 继续由 FastAPI 提供，包括 `/api/vue/*`、`/api/challenge/*`、BookLearner API、音频和图片接口。

## 文档入口

- `PROJECT_STATUS.md`：长期目标、当前状态、流程和优先级。
- `STYLE_GUIDE.md`：全局样式地图、视觉规则和样式验证清单。
- `VUE_MIGRATION_STATUS.md`：Vue 化迁移流水账和历史拆分记录。
- `README.md`：项目启动、Excel 导入、词典/音频/BookLearner 基础说明。

## 每轮工作流程

1. 先读 `PROJECT_STATUS.md` 和相关专项文档，不做全量扫。
2. 运行最小状态检查：
   - `git status --short`
   - `git log -1 --oneline`
3. 按当前用户反馈或优先级定点修改。
4. 代码修改后验证：
   - 优先运行 `powershell -ExecutionPolicy Bypass -File scripts\verify-release.ps1`
   - `npm run build`，工作目录 `frontend`
   - Python 入口或相关模块编译检查
   - 必要时做 HTTP 或浏览器验证
5. 提交并推送 `main`。
6. 运行 `powershell -ExecutionPolicy Bypass -File scripts\deploy-production.ps1` 部署到生产服务器。
7. 线上检查：
   - 关键 URL 返回 200
   - 浏览器无明显 console error
   - 运行 `powershell -ExecutionPolicy Bypass -File scripts\check-production-logs.ps1`
   - `spelling-bee-star.service` 日志无 `Traceback`、`ERROR`、`Exception`、500
8. 如本轮改变了项目结构、样式规则、部署方式或下一步优先级，更新 Markdown。

## 固定验证 URL

- `/`
- `/lists`
- `/words/1?edit=1&list_id=24`
- `/challenge/24`
- `/booklearner`
- `/challenge-calendar/2026-06-16`

## 下一步优先级

- 继续根据真实页面反馈修复 Vue 化后的样式变形。
- 保持挑战页音频、自动学习、拼写提交、错误复盘数据链路稳定。
- 发现中文乱码时先用 UTF-8 读取确认，避免被 PowerShell 控制台编码误导。
- 大改 Vue 组件前先看 `STYLE_GUIDE.md`，优先复用现有类名和 token。
- 对新需求默认完成本地验证、Git 提交、推送、服务器部署和线上检查。
- 后续继续把浏览器视觉巡检和常见页面回归检查脚本化。
