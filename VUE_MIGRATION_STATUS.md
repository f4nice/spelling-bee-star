# SpeakEasy Vue 化进度说明

这份说明用于减少每轮重复扫描和上下文消耗。每轮仍以当前工作树、线上状态和命令输出为准；本文件只作为方向锚点。

## 当前状态

- 主入口已切到 Vue shell：`app/templates/vue_app.html` 挂载 `#speakeasy-vue-app`，入口为 `app/static/vue/speakeasy-app.js`。
- 主要 Vue 源码在 `frontend/src/app`，挑战页源码在 `frontend/src/challenge`。
- 后端路由仍由 `app/main.py` 返回统一 Vue shell，并通过 `/api/vue/*`、挑战 API、BookLearner API 提供数据。
- 线上地址：`http://47.116.28.2:8010`。
- GitHub `main` 分支持续提交部署。

## 已 Vue 化/已拆分重点

- 页面/出口：列表、列表详情、单词详情、挑战页、挑战日历、英文小报、好词好句、上传、导入预览、生词本等已进入 Vue route outlet/page/component 结构。
- 路由与数据：已拆出 route matchers、route loaders、route API paths、page context builders。
- 单词详情：图片、音频、录音、定义编辑、导航等已拆为组件、props helper 和 composable。
- 列表工具：上传、批量图片、删除、重命名、图片同步等已拆出 API path、form helper 和 composable。
- BookLearner：分析、保存、详情、历史、上传 workspace 已拆为多个组件和 action/data composable。
- Shell/Home：侧边栏导航派生、首页统计卡片配置已下沉到 JS helper。
- 构建产物：Vite shared chunk 使用哈希文件名，部署时要避免入口和 chunk 版本错配。

## 当前进行中

- 继续把偏大的 Vue 组件、composable、页面配置拆成小组件或 helper。
- 继续检查源码是否存在真实中文乱码；PowerShell `Get-Content` 可能假乱码，需用 Node 读取 UTF-8 确认。
- 继续把 FormData、props 装配、卡片配置、路由派生这类非渲染逻辑从 `.vue` 中移出。

## 下一步候选

- `frontend/src/app/components/BooklearnerUploadWorkspace.vue`
- `frontend/src/app/components/WordAudioOptionList.vue`
- `frontend/src/app/pages/UploadPage.vue`
- `frontend/src/app/components/ListsToolsPanel.vue`
- `frontend/src/app/composables/useImportPreviewForm.js`
- `frontend/src/app/components/ImportPreviewToolbar.vue`
- `frontend/src/app/components/BatchImageToolCard.vue`
- `frontend/src/app/components/BooklearnerHero.vue`
- `frontend/src/app/shellContext.js`

## 每轮固定检查

1. 先检查工作树和热点：
   - `git status --short`
   - `git log -1 --oneline`
   - 统计 `frontend/src/app` 下 `.vue`/`.js` 行数热点
   - 搜索旧模板/旧逻辑边界：`TemplateResponse`、`x-data`、`Alpine`、`onclick`、`innerHTML`、`querySelector`、`addEventListener`
2. 修改后必须运行：
   - `npm run build`，工作目录 `frontend`
   - `py -3 -m py_compile app\main.py`
   - Node UTF-8 乱码扫描
3. 提交并推送 `main`。
4. 部署到服务器后验证：
   - 关键页面 HTTP 200
   - 浏览器控制台无 error
   - `spelling-bee-star.service` 日志无 ERROR/Traceback/Exception/500

## 部署注意事项

- SSH alias：`caishenye-aliyun`
- 线上目录：`/opt/spelling-bee-star`
- systemd 服务：`spelling-bee-star.service`
- 文件 owner/group：`spellingbee`
- 不输出、不保存服务器密码明文。
- 若 `app/static/vue` 中哈希 chunk 变化，优先同步整个 `app/static/vue` 目录或确保入口与 chunk 同版本。

## 关键验证 URL

- `/`
- `/lists`
- `/lists/24`
- `/upload`
- `/booklearner`
- `/wrong-words`
- `/challenge/24`
- `/challenge/24?daily_count=20&start_count=0`
- `/words/1?edit=1`
- `/newspaper`
- `/newspaper/world/0`
- `/challenge-calendar/2026-06-18`
