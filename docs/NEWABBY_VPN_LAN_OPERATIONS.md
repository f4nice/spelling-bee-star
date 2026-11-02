# 阿里云经 NEWABBY 访问本地网络

2026-11-02 现场配置与验收记录。不含密码、证书私钥、API密钥或业务数据。

## 拓扑与访问范围

```text
阿里云 139.224.9.235（OpenVPN 10.67.0.1）
  -> 已有 OpenVPN 隧道
NEWABBY 10.67.0.3 / 192.168.1.104
  -> ens18，源地址转换为192.168.1.104
本地 192.168.1.0/24（含量化雷达192.168.1.200）
```

仅允许阿里云本机使用 `10.67.0.1` 源地址，经此隧道主动访问本地网段，并允许对应回包。未向互联网公开内网，未自动授权NAS等其他VPN客户端，也未把WireGuard `10.66.66.0/24` 接入本地网络。访问目标仍受其自身防火墙、登录和业务权限限制。

本地设备看到的来源是 `192.168.1.104`，因此不需要改家庭网关或逐台加回程路由。代价是目标日志不能仅凭来源IP区分云端调用，应保留应用认证和日志。全LAN访问权限由已获授权的阿里云主机持有，请保护其管理员权限。

## 本次变更

- 云端现场已存在内核路由 `192.168.1.0/24 via 10.67.0.3 dev tun0`，以及已加载的 CCD `iroute 192.168.1.0 255.255.255.0`。没有重复添加CCD或新建VPN身份。
- 在备份后，仅向 `/etc/openvpn/server/newabby.conf` 追加 `route 192.168.1.0 255.255.255.0 10.67.0.3`，让既有路由在下次VPN启动时保留。没有推送到其他客户端，没有改默认路由，没有为本次变更重启共享VPN。
- 104的IP转发原已由Docker开启；真正阻断中转的是 `FORWARD DROP` 下没有 VPN-LAN 放行规则。
- 仅新增3条带 `newabby-cloud-lan-20261102` 注释的iptables规则：`DOCKER-USER` 中的单云端地址到LAN放行、仅已建立连接的回包放行，以及限定 `-s 10.67.0.1/32 -d 192.168.1.0/24 -o ens18` 的SNAT。
- 既有Docker规则和现场原有的较宽SNAT均未删除或改写；本次新增规则独立标记，位于前部。禁止用全表恢复、flush、全局 ACCEPT 或重启防火墙来撤销本次规则。
- `newabby-vpn-lan.service` 已启用并active，在Docker和独立VPN启动之后幂等检查/添加3条规则。不依赖一次性的手工iptables操作。没有为了验收重启主机或生产Docker；不声称真实重启演练已经完成。
- 未修改股票服务器配置或交易开关，未登录量化雷达SSH；现有密钥的只读认证尝试被拒绝。TCP/HTTP可达与SSH登录权限是两回事。

## 使用

在阿里云主机上直接用内网地址访问，例如：

```sh
ping -c 3 192.168.1.200
curl -I http://192.168.1.200:8000/login
curl -I http://192.168.1.104:8012/login
```

量化雷达 `/health` 当前受登录门禁保护，未认证返回302，跟随跳转到 `/login/phone` 为200；不能把302误判成VPN失败，也不能把登录页200当作认证后的业务/交易验证。

本地电脑仍正常直接访问本地网段，无需改默认网关。NEWABBY数据库仍只监听 `127.0.0.1:3307`，云端连接 `.104:3307` 被拒绝。

## 状态检查

104上：

```sh
systemctl is-active openvpn-client@newabby104 newabby-vpn-lan
systemctl is-enabled openvpn-client@newabby104 newabby-vpn-lan
python3 /opt/newabby-network/vpn-lan-20261102/gateway.py status
iptables -nvL DOCKER-USER
iptables -t nat -nvL POSTROUTING
ip route get 139.224.9.235
```

阿里云上：

```sh
ip route get 192.168.1.200
python3 /etc/openvpn/server/backups/vpn-lan-20261102/cloud.py status
systemctl is-active openvpn-server@newabby nginx
```

104的默认路由及阿里云端点应仍走 `192.168.1.1/ens18`。云端到量化雷达应走 `10.67.0.3/tun0`，源地址 `10.67.0.1`。

如果有人清空了iptables或修改Docker规则，先核查原因，再手动运行 `python3 /opt/newabby-network/vpn-lan-20261102/gateway.py ensure` 可幂等补回仅本次3条规则；不要重复运行一次性 `install`。

## 备份与受控回退

- 104：`/opt/newabby-network/vpn-lan-20261102/`，有 `iptables-before.txt`、生产容器/默认路由/PID基线 `before.json`、安装回执和限定脚本。
- 阿里云：`/etc/openvpn/server/backups/vpn-lan-20261102/`，有 `newabby.conf.before`、PID/默认路由基线、变更回执和限定脚本。
- 两处目录0700、备份0600。不要把私有现场备份复制到公开目录或提交Git。

需要撤销时，先明确授权并检查无并发变更。104执行：

```sh
python3 /opt/newabby-network/vpn-lan-20261102/gateway.py rollback
```

这只停用/删除本次独立规则服务及3条带标识的规则，保留原Docker/NAT、VPN、应用、数据库和全部备份，不恢复整张旧iptables表。服务没有自动清理规则的ExecStop；单纯 `systemctl stop` 不等于撤销访问。

云端执行 `python3 /etc/openvpn/server/backups/vpn-lan-20261102/cloud.py rollback` 会在指纹完全匹配时只撤销本次配置追加块，保留变更前就已存在的内核运行路由，不重启VPN；如还需删除运行路由，应另行评估现有依赖，不自动扩展回退范围。

## 本轮验收边界

11项合成测试在本机与两端远端通过。真实阿里云到量化雷达ping 3/3成功、延迟约12ms，量化雷达最终登录页200，SSH22 TCP可达；NAS5000、NEWABBY LAN8012、公网登录均200，本地网关ping成功。3条规则有命中，重复ensure无重复规则；104数据库3307未暴露，NEWABBY本地登录200、匿名词表401。

前后NEWABBY应用/数据库容器ID、启动时间、重启计数和默认路由保持一致；104 VPN PID48385、云端VPN PID829778和Nginx PID6305未变。最终只读验收将整个iptables规则集去除仅本次注释规则、忽略计数器/生成时间后，与原备份严格比较完全一致。没有改家庭路由器、NAS网络、共享WireGuard、防火墙默认策略、股票服务或交易状态。

未扫描整个/24，未验证每台设备/每个端口，未做真实主机重启演练，未配置新的公网域名反向代理。后续如需从另一台云服务器或VPN客户端访问，需要独立授权并明确来源范围。
