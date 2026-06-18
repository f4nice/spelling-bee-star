# SpeakEasy Style Guide

本文件记录 Vue 化后的全局样式地图。后续改 UI 时先读这里，再定点看 CSS 和组件，避免每次全站重新扫。

## 样式入口

- 全局样式：`app/static/styles.css`
- 主 Vue 应用：`frontend/src/app`
- 挑战页 Vue 应用：`frontend/src/challenge`
- 构建产物：`app/static/vue`
- 模板入口：`app/templates/vue_app.html`

不要手改 `app/static/vue` 里的构建产物。修改 Vue 后在 `frontend` 目录执行 `npm run build`，让 Vite 重新生成。

## 当前视觉方向

- 气质：安静、清爽、适合长期学习，不做营销页式大装饰。
- 主色：绿色系作为学习进度和主操作提示，背景保持低饱和米白灰。
- 圆角：普通控件 8px，主要面板和卡片 12px。
- 阴影：只用于可点击卡片、浮层、顶部栏和重点容器，避免页面满屏漂浮。
- 信息密度：列表、挑战、单词详情都优先可扫描，不做过高卡片或过大的标题。
- 图片：保持真实内容可见，列表卡片图片固定高度，内容区不要撑出大空白。

## CSS 分区速查

- 根变量、顶部栏、侧边栏：`app/static/styles.css` 顶部 `:root` 到 `.side-nav`
- 首页统计和导入工具：`.home-*`、`.lists-tools-panel`、`.tool-card`
- 通用面板、表单、按钮、卡片：`.panel`、`button`、`.word-card`
- 首页挑战日历：`.challenge-calendar`、`.calendar-day`、`.calendar-total`
- 挑战答题页：`.challenge-panel`、`.challenge-word-body`、`.speech-audio-player`、`.challenge-answer-panel`
- 单词详情页：`.detail-panel`、`.word-title-stack`、`.audio-row`、`.definition-list`
- BookLearner：`.booklearner-page`
- 响应式规则：文件底部的 `@media` 区域

## 修改规则

- 优先改 `:root` 里的 token，再改具体组件。
- 新增页面组件时复用 `.panel`、`.secondary-button`、`.ghost-button`、`.word-card` 等已有类。
- 不要在 Vue 组件里写大段 inline style；需要复用的样式放回 `app/static/styles.css`。
- 只在控件、重复卡片、浮层上用卡片样式；页面区块尽量保持自然布局。
- 文件上传控件统一用自定义 picker 样式，避免直接暴露原生文件输入。
- 按钮禁用态必须避免 hover 阴影和位移。
- 挑战页音频优先使用播放器样式，不退回纯文字按钮。

## 本轮全局美化记录

- 增加全局色彩、圆角、阴影、focus ring token。
- 顶部栏、侧边栏、面板、按钮、输入框统一视觉层次。
- 首页和列表页卡片增加轻微 hover 和紧凑内容区。
- 导入页文件选择器统一成自定义虚线按钮样式。
- 日历格子重做层次，今日、记录日、数量胶囊更清晰。
- 挑战页图片区、答题区、浏览器朗读播放器和输入框统一成学习卡片风格。
- 单词详情页的自动学习、音频候选、录音、内联编辑框统一圆角和背景。

## 验证清单

样式修改后至少检查：

- `/`
- `/lists`
- `/words/1?edit=1&list_id=24`
- `/challenge/24`
- `/booklearner`
- `/challenge-calendar/2026-06-16`

本地或发布前执行：

```powershell
npm run build
```

工作目录为 `frontend`。如果只改 `app/static/styles.css` 和文档，构建不是必须，但发布前跑一次更稳。

发布后检查服务状态和日志，确认没有 `Traceback`、`ERROR`、`Exception` 或 500。
