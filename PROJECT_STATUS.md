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
- Vue 覆盖检查脚本：`scripts/check-vue-coverage.ps1`
- 线上日志检查脚本：`scripts/check-production-logs.ps1`
- 生产部署脚本：`scripts/deploy-production.ps1`
- 固定验证 URL 清单：`scripts/verification-urls.json`
- 版本矩阵默认模板：`VERSION_MATRIX.default.json`
- 运行时版本矩阵：`uploads/version_matrix.json`，首次启动从默认模板生成并补机器码；部署不会覆盖这个运行时文件。
- 上传运行目录：生产服务使用 `spellingbee` 用户；部署脚本会保留 `uploads/` 并把它归还给 `spellingbee:spellingbee`，避免 Excel 预览、图片、音频上传写入失败。

## 当前功能记录

- 2026-06-19：`/lists` 我的单词表页把“导入单词”和“批量上传图片”收进“新建单词表”弹层；页面主体只保留单词表卡片，标题右侧提供弹层入口。
- 2026-06-19：单词详情页的英文定义、中文定义、英文例句默认完整文本展示，不再直接显示输入框；可编辑状态下双击文本进入编辑，失焦保存。
- 2026-06-19：单词详情页图片工具改为“修改图片”弹层，上传图片、上传预览保存、网络找图和候选图保存都在弹层内完成。
- 2026-06-19：`/lists` 单词表卡片标题去掉右侧独立“xx 词”徽标，只保留挑战摘要和挑战入口。
- 2026-06-19：`/lists` 单词表卡片下方去掉“挑战进度”文本和进度条，只保留“挑战几个”输入框与“开始挑战”按钮。
- 2026-06-19：`/lists/{id}` 列表详情页去掉全局标题条；列表名称默认文本显示，双击编辑，失焦/回车保存；“保存名称”按钮移除，“继续导入”放到单词数量右侧。
- 2026-06-19：好词好句、英文小报、我的生词本相关路由去掉全局 `SpeakEasy + 页面名` 标题条，保留页面内部内容标题。
- 2026-06-22：新增全站版本矩阵。左侧栏展示按模块划分的版本矩阵，公共页脚展示版本号和机器码，上传/导入/书籍上传等公共区域展示同源版本戳；版本号以后优先维护 `uploads/version_matrix.json`，不要直接改构建产物。
- 2026-06-22：修复单词表弹层上传操作。Excel 上传和批量图片上传现在有上传中与错误提示；部署时会自动修复生产 `uploads/` 权限，防止预览 JSON 或图片写入被拒绝。
- 单词详情页音频区使用 `WordAudioManagerModal.vue` 管理音源：入口按钮为“音频管理”。
- 音频管理弹窗包含四个区块：重新获取候选音源并试听保存、AI 朗读生成并保存为美音/英音、录制音频占位入口、上传本地音频并预览后保存。
- 候选音源保存走 `/api/vue/words/{word_id}/audio-choice`，上传音频保存走 `/api/vue/words/{word_id}/recorded-audio`。
- AI 朗读保存走 `/api/vue/words/{word_id}/ai-audio`，支持 `AI_TTS_PROVIDER=openai` 或 `aliyun`。OpenAI 配置：`OPENAI_API_KEY`、`OPENAI_TTS_MODEL`、`OPENAI_TTS_VOICE_US`、`OPENAI_TTS_VOICE_GB`；阿里云智能语音交互配置：`ALIYUN_NLS_APPKEY`、`ALIYUN_NLS_TOKEN` 或 `ALIYUN_ACCESS_KEY_ID`/`ALIYUN_ACCESS_KEY_SECRET` 自动换 Token、`ALIYUN_TTS_GATEWAY`、`ALIYUN_TTS_FORMAT`、`ALIYUN_TTS_SAMPLE_RATE`、`ALIYUN_TTS_VOICE_US`、`ALIYUN_TTS_VOICE_GB`。
- 录制音频完整流程尚未接入弹窗，当前保留禁用入口，后续优先复用既有录音 API 和播放器样式。
- 列表详情页的单词卡片图片使用自适应完整显示，避免文字图或方图被固定裁切。

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
   - Vue 页面/路由覆盖由 `scripts/check-vue-coverage.ps1` 在验证脚本中自动检查
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

固定 HTTP 冒烟检查 URL 维护在 `scripts/verification-urls.json`，`scripts/verify-release.ps1` 会自动读取这份清单。

## 下一步优先级

- 继续根据真实页面反馈修复 Vue 化后的样式变形。
- 保持挑战页音频、自动学习、拼写提交、错误复盘数据链路稳定。
- 继续完善单词详情音频弹窗里的录音流程，并保证上传后可预览、可回放。
- 发现中文乱码时先用 UTF-8 读取确认，避免被 PowerShell 控制台编码误导。
- 大改 Vue 组件前先看 `STYLE_GUIDE.md`，优先复用现有类名和 token。
- 对新需求默认完成本地验证、Git 提交、推送、服务器部署和线上检查。
- 后续继续把浏览器视觉巡检和常见页面回归检查脚本化。

- 2026-06-19：我的生词本日期卡片使用当天错词的真实封面图，避免 Vue 卡片固定显示叉号占位。

- 2026-06-19：拼写挑战输入框限制为英文拼写字符，输入或粘贴数字、中文等会自动过滤。
- 2026-06-19：拼写挑战答错后显示正确答案弹窗，点击“我知道了”或按回车后再进入下一个单词。

- 2026-06-19：修复 Vue 全局标题隐藏判断使用 ref 的问题，拼写挑战等页面不再显示顶部 SpeakEasy 页面标题条。

- 2026-06-19：拼写挑战错误弹窗在正确答案上直接标出匹配、漏输、输错和多输入的字符。
- 2026-06-19: BookLearner 详情页历史卡片补齐可点击跳转，历史接口返回封面 `coverUrl`；卡片优先显示真实书籍封面，没有封面时显示更像书摘封面的占位，不再固定显示 `B`。
- 2026-06-19: BookLearner 上传入口改为弹层；`/booklearner/upload` 直达时自动打开上传书籍弹窗。书摘详情页去掉 JSON 预览，改为摘要和“生成单词表”操作，并为分析/保存/生成单词表补充错误提示。
- 2026-06-19: 好词好句重构为以书籍为中心的摘录系统：首页按行展示好句，点击好句进入来源书籍详情；详情页顶部展示封面、作者、统计和生成单词表，中部展示该书其他好句，右侧展示难点单词，并保留上传弹层。
