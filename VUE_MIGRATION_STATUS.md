# SpeakEasy Vue 化工作台

这份文档是后续推进 Vue 化的主索引，用来减少每轮重复扫描和沟通成本。每轮优先读取这里的计划和当前进度，做定点检查后直接修改；等计划项基本完成后，再做一次全项目遗漏扫描。

## 目标

- 把 SpeakEasy / spelling-bee-star 的主要页面、旧模板逻辑和前端交互逐步收敛到 Vue 入口。
- 保持线上功能不变，优先拆组件、抽 props/helper/composable、修复真实中文乱码。
- 每次代码修改后仍必须构建、编译、提交、推送、部署并验证线上状态。

## 当前基线

- 主入口：`app/templates/vue_app.html` 挂载 `#speakeasy-vue-app`。
- Vue 源码：`frontend/src/app`；挑战页源码：`frontend/src/challenge`。
- 构建产物：`app/static/vue/speakeasy-app.js`、`challenge-app.js` 和 Vite shared chunk。
- 后端入口：`app/main.py` 返回统一 Vue shell，并通过 `/api/vue/*`、挑战 API、BookLearner API 提供数据。
- 线上地址：`http://47.116.28.2:8010`。
- 部署目标：`caishenye-aliyun:/opt/spelling-bee-star`，服务 `spelling-bee-star.service`。

## 已完成结果

- 页面出口已 Vue 化：主页、列表、列表详情、单词详情、挑战页、挑战日历、英文小报、好词好句、上传、导入预览、生词本。
- 路由和数据层已拆出：route matchers、route loaders、route API paths、page context builders。
- 单词详情已拆出：媒体面板、定义面板、音频面板、录音面板、图片工具、导航和相关 props/composable。
- 列表工具已拆出：上传、批量图片、删除、重命名、图片同步相关 API helper 和组件。
- BookLearner 已拆出：首页、历史、详情、上传分析 workspace、查询面板、结果面板、action/data composable。
- Shell/Home 已拆出：侧边栏导航派生、挑战进度、首页统计卡片配置。
- 近期提交：
  - `f0709f6`：抽出 BookLearner upload workspace props。
  - `25b3b2c`：抽出通用 Excel 上传表单。
  - `74be5ef`：抽出批量图片上传表单、列表工具 props helper。
  - `cbef214`：拆分 `UploadExcelForm.vue` 的 page/card 字段组件，并同步新 Vite chunk。
  - `ae6e42c`：拆分 `WordAudioOptionList.vue` 的候选项组件和 props helper。
  - `f80c5c3`：拆分导入预览工具栏 props、提交按钮和图片选择 helper。
  - `170514c`：拆分 `useImportPreviewForm.js` 的表单状态和 URL helper。
  - `cf3b750`：拆分 BookLearner Hero 动作区、精选书摘列表和 props helper。
  - `1a7dc31`：拆分 `shellContext.js` 的默认值、JSON 解析和 DOM 文本读取 helper。
  - `f67a080`：拆分 `useListDetailTools.js` 的列表重命名、删除和图片同步 action helper。
  - `e218ce6`：拆分 `WordCard.vue` 的媒体和挑战统计子组件，并修复卡片中文乱码。
  - 待提交：拆分 `ListDetailHeader.vue` 的标题编辑和单词数量子组件。

## 正在进行

- 当前推进区域：列表详情头部。
- 当前已改到：`ListDetailHeader.vue` 已瘦身，新增 `ListTitleEditor.vue` 承担标题输入和单词数量显示。
- 当前轮状态：本地 `npm run build`、`py -3 -m py_compile app\main.py`、Node UTF-8 乱码扫描已通过；等待提交、推送、部署和线上验证。

## 下一批改哪里

当前轻量计划队列继续按最终扫描候选推进。下一步先完成本轮提交/部署，然后再从下面候选中选择一个低风险拆分点。

最终扫描已记录的后续可选候选：

- `frontend/src/app/composables/useWordRecorder.js`：录音逻辑仍偏集中，后续可按 capture/state/actions 再拆。
- `frontend/src/app/composables/useListDetailTools.js`：已抽出 `listDetailActions.js`。
- `frontend/src/app/components/WordCard.vue`：已拆出媒体和挑战统计子组件。
- `frontend/src/app/components/ListDetailHeader.vue`：本轮已拆出 `ListTitleEditor.vue`，提交部署后可从候选中移除。
- `frontend/src/app/components/AppSidebar.vue`：组件体量中等，暂未发现必须立即处理的旧模板逻辑。
- `frontend/src/app/components/ImportPreviewTable.vue` 和 `frontend/src/app/forms/importPreviewFormState.js`：导入预览已拆一轮，后续只做低风险细化。
- 旧逻辑边界扫描目前主要命中预期项：`vue_app.html` shell、`app/main.py` 的 Vue shell 返回、Vue/浏览器事件监听、构建产物中的打包代码。

## 每轮轻量流程

为了少用流量和上下文，后续每轮不再做完整热点扫描，改成：

1. 读取本文件的“正在进行”和“下一批改哪里”。
2. 运行最小状态检查：
   - `git status --short`
   - `git log -1 --oneline`
3. 针对当前计划文件做定点读取和修改。
4. 修改后固定验证：
   - `npm run build`，工作目录 `frontend`
   - `py -3 -m py_compile app\main.py`
   - Node UTF-8 乱码扫描
5. 提交并推送 `main`。
6. 部署后验证：
   - 关键页面 HTTP 200
   - 浏览器控制台无 error
   - `spelling-bee-star.service` 日志无 ERROR/Traceback/Exception/500
7. 把本文件的“正在进行”和“已完成结果”更新到最新提交。

## 最终遗漏扫描

当“下一批改哪里”基本清空后，再执行一次全量扫描，而不是每轮都全扫：

- 工作树和提交：
  - `git status --short`
  - `git log -1 --oneline`
- 源码热点：
  - 统计 `frontend/src/app` 下 `.vue`/`.js` 行数前 30。
  - 搜索旧模板/旧逻辑边界：`TemplateResponse`、`x-data`、`Alpine`、`onclick`、`innerHTML`、`querySelector`、`addEventListener`。
- 乱码：
  - 用 Node 读取 UTF-8 扫描，不以 PowerShell `Get-Content` 显示为准。
- 后端模板：
  - 检查 `app/templates` 中是否还有真实页面模板承担交互。
  - 确认 `app/main.py` 中旧页面路由是否都返回 Vue shell 或 API 数据。
- 线上：
  - 全关键路径 HTTP 200。
  - 浏览器控制台无 error。
  - 服务日志无异常。

## 固定验证 URL

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

## 部署注意

- 不输出、不保存服务器密码明文。
- 文件 owner/group 使用 `spellingbee`。
- 如果 `app/static/vue` 中哈希 chunk 变化，要同步入口和 chunk 的同版本文件，避免线上入口与 chunk 版本错配。
