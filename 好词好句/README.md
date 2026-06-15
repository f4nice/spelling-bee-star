# BookLearner

BookLearner 是一个本地运行的读书学习工具。输入书名或作者名后，它会优先检索可公开访问的公版全文，自动整理：

- 经典短句
- 难点单词
- 单词释义
- 原文例句
- 阅读关注点

如果没有找到可分析的公版全文，系统只显示书籍元信息和下一步建议，避免编造语录。

## 运行

```powershell
py app.py
```

然后打开：

```text
http://127.0.0.1:8765
```

## 数据来源

- Gutendex / Project Gutenberg：用于查找公版全文。
- Standard Ebooks：用于补充可公开访问的公版全文。
- Open Library：用于在没有全文时补充书籍元信息。
- Internet Archive：用于补充书籍元信息和搜索提示。
- Google Books：用于补充书籍元信息和搜索提示；如果接口限流会自动跳过。
- Free Dictionary API：用于补充英文单词释义；网络不可用时会自动降级。

## MySQL

MySQL 用于保存每次分析的学习记录。当前项目在未配置 MySQL 时仍可正常运行，只是不保存历史。

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

如果你使用 Docker，可用下面命令启动 MySQL：

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
