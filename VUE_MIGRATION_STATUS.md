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
  - `3afc0c3`：拆分 `ListDetailHeader.vue` 的标题编辑和单词数量子组件。
  - `4dfb1fd`：拆分 `AppSidebar.vue` 的单个导航链接子组件。
  - `d9a9fc9`：拆分 `ImportPreviewTable.vue` 的表头和数据行子组件。
  - `5642ecf`：拆分导入预览表单行列选择 helper。
  - `e648933`：拆分单词录音 session helper。
  - `a2b0767`：拆分单词音频候选加载和选择 action helper。
  - `a0fb6f0`：拆分挑战日历词卡正文组件和详情链接 helper。
  - `5554f6a`：拆分单词定义可编辑字段配置 helper。
  - `2908642`：拆分列表详情页单词网格组件。
  - `fae8976`：拆分 BookLearner 页面路由分支组件。
  - `04cb26e`：拆分单词表卡片封面和正文子组件。
  - `be24c3e`：拆分首页挑战日历标题组件。
  - `78151ba`：拆分列表路由出口的列表总览和列表详情分支组件。
  - `1fd5dc0`：拆分单词图片工具栏的上传控件和动作按钮组件。
  - `5989f98`：拆分首页精选单词表标题和网格组件。
  - `f40d684`：拆分单词详情标题栈和标题动作组件。
  - `e24e5f8`：拆分单词定义字段的编辑/只读值组件。
  - `f77ae88`：拆分应用顶栏品牌链接和每日一句组件。
  - `93e4f4a`：拆分侧边栏导航列表组件。
  - 待提交：拆分单词卡片正文组件。

## 正在进行

- 当前推进区域：单词卡片。
- 当前已改到：新增 `WordCardBody.vue`，把单词标题、挑战统计和定义摘要从 `WordCard.vue` 中拆出；外层链接、序号和媒体展示保持不变。
- 当前轮状态：等待本地构建、Python 编译、乱码扫描、提交、推送、部署和线上验证。

## 下一批改哪里

当前轻量计划队列继续按最终扫描候选推进。下一步先完成本轮提交/部署，然后再从下面候选中选择一个低风险拆分点。

最终扫描已记录的后续可选候选：

- `frontend/src/app/composables/useWordRecorder.js`：已抽出 `wordRecorderSession.js`。
- `frontend/src/app/composables/useWordAudio.js`：已抽出 `wordAudioActions.js`。
- `frontend/src/app/components/ChallengeDayWordCard.vue`：已抽出正文组件和详情链接 helper。
- `frontend/src/app/components/WordEditableDefinitionFields.vue`：已抽出 `wordDefinitionFields.js`。
- `frontend/src/app/pages/ListDetailPage.vue`：已抽出 `ListDetailWordGrid.vue`。
- `frontend/src/app/pages/BooklearnerPage.vue`：已抽出 `BooklearnerRouteSections.vue`。
- `frontend/src/app/components/WordListCard.vue`：已抽出封面和正文子组件。
- `frontend/src/app/components/HomeChallengeCalendar.vue`：已抽出 `HomeChallengeCalendarHeading.vue`。
- `frontend/src/app/components/ListRouteOutlet.vue`：已抽出 `ListOverviewRoute.vue` 和 `ListDetailRoute.vue`。
- `frontend/src/app/components/WordImageTools.vue`：已抽出 `WordImageUploadField.vue` 和 `WordImageActionButtons.vue`。
- `frontend/src/app/components/HomeFeaturedLists.vue`：已抽出 `HomeFeaturedListsHeading.vue` 和 `HomeFeaturedListGrid.vue`。
- `frontend/src/app/components/WordDetailHeading.vue`：已抽出 `WordDetailTitleStack.vue` 和 `WordDetailHeadingActions.vue`。
- `frontend/src/app/components/WordEditableDefinitionItem.vue`：已抽出 `WordEditableDefinitionValue.vue`。
- `frontend/src/app/components/AppTopbar.vue`：已抽出 `AppBrandLink.vue` 和 `AppDailyQuote.vue`。
- `frontend/src/app/components/AppSidebar.vue`：已抽出 `SidebarNavList.vue`。
- `frontend/src/app/components/WordCard.vue`：本轮已抽出 `WordCardBody.vue`，提交部署后标记完成。
- `frontend/src/app/composables/useListDetailTools.js`：已抽出 `listDetailActions.js`。
- `frontend/src/app/components/WordCard.vue`：已拆出媒体和挑战统计子组件。
- `frontend/src/app/components/ListDetailHeader.vue`：已拆出 `ListTitleEditor.vue`。
- `frontend/src/app/components/AppSidebar.vue`：已拆出 `SidebarNavLink.vue`。
- `frontend/src/app/components/ImportPreviewTable.vue`：已拆出表头和行组件。
- `frontend/src/app/forms/importPreviewFormState.js`：已拆出行列选择 helper。
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
