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

默认使用免费开放词典接口：

```text
https://dictionaryapi.dev/
```

它可以返回英文定义、音标、例句和部分英式/美式发音音频。

韦氏词典是可选增强源。在 `.env` 中填写：

```env
MERRIAM_WEBSTER_API_KEY=你的韦氏API_KEY
```

未配置 Key 时，系统会自动使用免费开放词典，不会因为缺少韦氏 Key 导入失败。
