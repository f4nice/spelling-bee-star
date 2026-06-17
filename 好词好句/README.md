# BookLearner

BookLearner 是 SpeakEasy / spelling-bee-star 中的“好词好句”阅读学习模块。主项目已经把它接入 Vue 页面，常规使用请启动根目录应用后打开：

```text
http://127.0.0.1:8000/booklearner
```

兼容入口也会跳转到同一个 Vue 页面：

```text
http://127.0.0.1:8000/好词好句
```

## 本地 API

`好词好句/app.py` 现在只保留独立 API 服务，旧的 vanilla JS 静态页面已经退役，避免和主应用 Vue 入口重复维护。

```powershell
py app.py
```

默认地址：

```text
http://127.0.0.1:8765
```

可用接口包括：

- `GET /api/health`
- `GET /api/storage`
- `GET /api/history`
- `GET /api/history/{id}`
- `GET /api/suggest?q=...`
- `GET /api/analyze?q=...`
- `POST /api/analyze-text`

## 数据来源

- Gutendex / Project Gutenberg：查找可公开访问的公版全文。
- Standard Ebooks：补充可公开访问的公版全文。
- Open Library：在没有全文时补充书籍元信息。
- Internet Archive：补充书籍元信息和搜索提示。
- Google Books：补充书籍元信息和搜索提示；如果接口限流会自动跳过。
- Free Dictionary API：补充英文单词释义；网络不可用时会自动降级。

## MySQL

MySQL 用于保存每次分析的学习记录。项目未配置 MySQL 时仍可正常运行，只是不保存历史。

安装依赖：

```powershell
py -m pip install -r requirements.txt
```

复制配置：

```powershell
Copy-Item .env.example .env
```

编辑 `.env` 后初始化数据库：

```powershell
py scripts/init_mysql.py
```

如果使用 Docker，可以启动 MySQL：

```powershell
docker compose up -d mysql
```

Docker 默认账号：

```text
database: booklearner
user: booklearner
password: booklearner-pass
root password: booklearner-root
```

对应 `.env` 可设置：

```text
BOOKLEARNER_MYSQL_ENABLED=1
BOOKLEARNER_MYSQL_HOST=127.0.0.1
BOOKLEARNER_MYSQL_PORT=3306
BOOKLEARNER_MYSQL_DATABASE=booklearner
BOOKLEARNER_MYSQL_USER=booklearner
BOOKLEARNER_MYSQL_PASSWORD=booklearner-pass
BOOKLEARNER_MYSQL_ADMIN_USER=root
BOOKLEARNER_MYSQL_ADMIN_PASSWORD=booklearner-root
```

## 使用建议

适合优先搜索英文公版书，例如：

- Pride and Prejudice
- The Great Gatsby
- Jane Eyre
- The Adventures of Sherlock Holmes

也可以直接粘贴你有权学习使用的文本片段进行分析。

## 测试

```powershell
py -m unittest discover -s tests
```
