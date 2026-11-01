# NEWABBY Linux104 运维说明

最后现场验收：2026-11-02。本文不含密码、API 密钥、登录令牌或业务数据。

用户确认的后续工作方式：**直接在新服务器核对、备份和操作，以 `/opt/newabby` 的实际运行状态为准。** 改动先在新机候选副本测试，再按当次授权应用；不直接用旧本地工作树或 NAS 包覆盖新机。旧 NAS 仅用于需要时只读核对历史备份，不再是发布目标。此约定不扩大任何一次任务的权限范围。

## 当前运行位置

| 项目 | 当前值 |
| --- | --- |
| 公网网站 | `https://www.newabby.com/` |
| 应用服务器 | `192.168.1.104`，Rocky Linux 10.1，80 GiB 虚拟磁盘 |
| 局域网入口 | `http://192.168.1.104:8012/` |
| 项目根目录 / Compose | `/opt/newabby` / `/opt/newabby/compose.json` |
| 应用容器 / 运行 UID | `newabby-app` / `10001:10001` |
| 数据库容器 | `newabby-mysql`，MySQL 8.4.11 |
| 正式数据库 | `newabby_permissions_live_20261101` |
| 数据库网络 | 主机仅 `127.0.0.1:3307`，应用内部使用 `db:3306`；不向局域网开放数据库 |
| 公网代理 | `139.224.9.235`，NEWABBY 唯一上游为 `10.67.0.3:8012` |
| 新机独立 VPN | `openvpn-client@newabby104`，地址 `10.67.0.3`，仅 VPN 网段入隧道 |

源码完整包在 `/opt/newabby/app`，静态资源在 `/opt/newabby/static`，BookLearner 在 `/opt/newabby/booklearner`，三者只读挂载。图片、音频及其他上传位于 `/opt/newabby/uploads`，数据库持久化位于 `/opt/newabby/mysql`。保留这两个数据目录，不要把容器删除与数据目录删除混为一谈。

Compose 和 `/opt/newabby/private` 中含有效私有配置，只允许管理员读取；禁止 `cat` 到聊天/日志，禁止提交 Git。验证 Compose 用 `config --quiet`，不要打印展开后的配置。

## 状态、启动和停止

在新服务器的管理员终端中使用：

```sh
docker compose -f /opt/newabby/compose.json ps
systemctl is-active docker openvpn-client@newabby104
docker compose -f /opt/newabby/compose.json config --quiet
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8012/login
```

正常登录页应返回 `200`；未登录访问 `/api/vue/lists` 应返回 `401`，不是故障。

需要启动 NEWABBY 时：

```sh
docker compose -f /opt/newabby/compose.json up -d
```

只停止或重新启动应用，不操作数据库及其他项目：

```sh
docker compose -f /opt/newabby/compose.json stop app
docker compose -f /opt/newabby/compose.json up -d --no-deps app
```

Docker 和独立 VPN 已开机启用，两个容器均为 `unless-stopped`。手动停止的容器不会因重启电脑而自动恢复，之后需手动启动；不要把这一行为当作启动故障。此次迁移验证了目标数据库容器重建后的持久化与账号接口，没有为了测试而重启整台服务器。

不要使用 `down -v`、删除持久化目录、全局 Docker prune，或重建无关容器。应用更新时，先备份并核对完整包和私有配置，再仅重建 `app`，不要只同步 `main.py`。

## NAS 保留范围及回退限制

NAS `192.168.1.247` 的原目录 `/volume1/docker/newabby-staging`、原 Compose 目录 `/volume1/docker/newabby-staging-run`、原正式库、旧库、图片音频及备份均保留。原应用 `newabby-staging-app-run` 已停止，维护门禁保留；NAS 其他容器、数据库服务和默认路由未因本次切换被重建或修改。

新机已开放后可能已有正常写入。**不能直接启动 NAS 旧应用或把代理指回 `10.67.0.2`，否则会形成双写或丢失新数据。** 如需回退，应先停止新机写入，备份并核对新机最新数据，再制定受控反向同步方案。

历史 `scripts/deploy-production.ps1` 默认仍是旧 Ubuntu 工作流，不能直接用于当前服务器。旧 Ubuntu、NAS 原目录都不是当前发布目标。

## 迁移验收与证据

- 最新冻结备份 SHA-256：`473f62e83bbc17d3e8b536cc96fbabf0a9232d5aa955ada12533b2f6f70dff6d`。
- 37 张表完整恢复前后原字段、行数及内容指纹一致；新机演练库单独保留，不作为网站运行库。
- 最终 201749 个媒体文件共 10006022127 字节，全部路径/大小/mtime 与 505 个内容 SHA-256 抽样校验通过；最后增量传输约 45 MB，无文件删除。不将元数据校验等同于全部文件重新逐字节哈希。
- 四个真实活跃账号各 11 类业务 API、账号隔离、公共词只读、图片音频及 68 个静态文件的维护期和公网 HTTPS 验收通过；未在真实账号答题、购买或领奖。
- 全部 13 个现有上传目录逐个通过容器实际 UID10001 的人工文件写入、读回、删除探针，探针全部清理，没有替换用户真实图片或音频。局域网登录页 200；不带 www 的原域名保留 HTTPS 跳转，最终到 `https://www.newabby.com/login` 返回 200。
- HTTP 预检后 36 张业务表和非新闻缓存不变；公共英文小报缓存的预期刷新单独核对。开放后不声称并发运行的整库永远不变。
- Nginx 只替换一个 NEWABBY 上游，其他共享站点配置字节保留。首次即时健康探测失败及自动恢复记录保留；第二次使用有界收敛等待通过。共享 Nginx/OpenVPN 主进程未重启。
- 临时受限直传公钥已从 NAS 撤销，专用只读导出挂载已卸载；新机实际认证拒绝。仅本次生成的临时私钥已删除，无恢复副本；VPN 私钥保留。
- 群晖唯一停用的临时 root 任务 `NEWABBY-Linux104-20261101-FinalSync` 已在用户操作时确认后仅删除入口，清单为空；所有脚本、数据库及媒体备份仍保留。入口可按保留材料重新建立，但不要重复执行已完成的一次性迁移。

完整业务快照和私有验收日志只留 NAS/新机，不在电脑或 Git 中保存：

- NAS：`/volume1/docker/newabby-staging/backups/linux104-migration-20261101/`
- 新机迁移工具/快照：`/opt/newabby-migration-20261101/`
- 新机恢复及公网验收回执：`/opt/newabby/proof/`、`/opt/newabby/state/`
- 公网代理首次及 retry2 证据：`/etc/nginx/backups/newabby-linux104-20261101/`
- 本机安全状态回执与截图：`.local-sync/linux104-migration-20261101/`，被 Git 忽略。

不得重新运行一次性迁移/恢复脚本，不得覆盖已有正式库或把原冻结备份误称为新机开放后的最新数据。后续备份计划属于独立运维事项，本次没有新增自动备份任务。

## Abby 历史数据恢复（2026-11-01 已完成）

账号 ID=2（abby / `u:2`）已按用户授权，取得拆分前共享词表、学习历史与错词的独立副本；不是把 jerry 的原行改归属。354 张词表中，250 张在“我的单词表”显示，其余 104 张属于历史生词本/系统表；35100 个私人词条、28675 次拼写历史、1118 条错词历史及既有 50 条公共词库进度保留。各账号之后继续独立。

abby 自身的 22 篇作文、1 篇日记（2026-10-22）、22 个猫咪档案和背包没有被旧备份重置；历史学习能量衔接后，正常公网猫咪接口验收可用 10137、已花 76051、累计 86188，未重复发奖。这些能量值是验收时快照，之后学习和购买会正常改变，不能当永久基线。

图片音频副本位于 `uploads/users/u2/images/` 和 `uploads/users/u2/audio/` 下的 `abby-recovery-20261101-<hash>.*`；105456 文件共 5527880047 字节，使用独立 inode/COW 副本并逐文件核对内容，原媒体未替换。个人媒体授权只接受既有的固定路径层级，不要再加一层恢复任务目录，也不要放宽授权来适配错误目录。

恢复材料均在新机私有 `/opt/newabby-recovery/abby-20261101/`：`before/` 是首轮完整备份，`before-live/` 是正式复制前最新 37 表备份，`source/` 保留旧共享导出、ID 映射与媒体映射，`proof/` 保留演练、首轮媒体 403 失败、修正、正式事务与四账号公网验收。正常猫咪接口验收另留 `/opt/newabby/state/abby-recovery-cat-live.json`。快照不在电脑或 Git 中保存；本次临时验证库验收后清理，原正式库、旧迁移演练库、NAS 原数据及备份保留。

**不要重复执行本次恢复脚本，也不要再次导入历史学习/错词数据。** 若仍报告空白，先检查当前登录账号和右上角“查看数据”：jerry 本人的日记为 0，abby 的历史日记不会自动显示到 jerry 空间。本人编辑需登录 abby，管理员也可在菜单只读查看 abby；不能关闭隔离或混合两人的私有写作记录。

## 后台删除密码设置（2026-11-02 已发布）

入口为“后台管理 → 网站管理 → 删除安全设置”，发布号 `BIZ-REL-20261102-001`、后台版本 `v20261102.1`，代码 `c8f2d47`，表单样式 `43e8e91`。

- 只有管理员在本人可写空间能修改；老师、只读用户、停用账号以及管理员的只读查看均不能修改，后台权限位不能代替管理员角色。
- 未填新密码时继续使用原 `LIST_DELETE_PASSWORD`，不创建文件、不显示或回填原密码。此次发布没有替换现有密码。
- 修改时输入两次 6–128 位新删除密码，并输入当前管理员的账号登录密码确认。仅保存密码哈希；新密码下一次删除即生效，不用再重启应用。
- `SITE_SECURITY_SETTINGS_FILE=/app/release-state/site-security.json` 使用已有持久化 state 挂载，对应主机 `/opt/newabby/state/site-security.json`。目录 UID10001、0700；保存后的文件为 0600。该路径不在 `/media` 或 `/static` 中，禁止把它移入公开 uploads 或提交 Git。
- 若此覆盖文件不存在，沿用服务器环境密码；文件存在但格式或权限异常时拒绝删除，不悄悄降级回原密码。未来应用更新需保留 state 目录、该环境配置及覆盖文件，不能用旧部署配置意外重置它。
- 不改变原环境密码或登录签名种子，因此删除密码修改不会使现有登录会话失效。词表及单词组删除共用该全站设置，账号数据隔离规则不变。

本次备份与发布证据在新机私有 `/opt/newabby-releases/delete-security-20261102/`；`before/database/` 为停写后的 37 表完整备份，`before/compose.json`、后端和静态资源原件也保留。候选以人工 SQLite 验证完整保存/重读及人工词表删除；线上只做空白保存和拒绝请求，不修改实际密码、不删除真实词表。发布期 37 表校验一致，维护期和公网四账号权限/隔离、68 个资源 HTTP 内容哈希通过，数据库容器未重建。不要重新运行这次一次性脚本，也不要在站点开放后用该快照回覆盖并发新数据。
