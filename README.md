# IPNotifier

每三分钟检查本机 IPv4 地址，变化时通过 SMTP 发送邮件。使用 Python 3.9+，无需管理员权限。

## 配置与运行

在仓库根目录安装依赖：

```sh
python3 -m pip install -r requirements.txt
```

编辑根目录 `.env`，填写 SMTP 主机、端口、用户名、密码或授权码，以及发件邮箱 `MAIL_FROM` 和收件邮箱 `MAIL_TO`（单个地址）。首次克隆后可执行 `cp .env.example .env` 创建配置；不要覆盖已有配置。

- `SMTP_SECURITY=ssl`：连接时加密，通常使用端口 465。
- `SMTP_SECURITY=starttls`：连接后升级为加密连接，通常使用端口 587。

具体参数以邮箱服务商说明为准。`.env` 已加入忽略规则，不要提交真实凭据。配置固定从仓库根目录读取，修改后需要重启程序。

```sh
python3 src/ip_notifier.py
```

启动时立即检查，首次成功获取 IP 只记录基线，不发邮件。每轮结束后等待 180 秒；IP 变化时发送包含新旧 IP 的邮件。按 `Ctrl+C` 退出。

获取 IP 失败时保留基线继续检查；发信失败时保留上次成功通知的 IP，下轮针对当前 IP 重试。若恢复原 IP，则不再通知。重启会重新建立基线，不补发停机期间的变化。检测仅反映采样时刻的 IP。

## 原理与范围

使用 UDP 套接字让系统选择访问 `1.1.1.1` 的路由，再读取本机源地址。检测 IP 不发送应用数据包，不进行 DNS 查询；邮件发送需要连接 SMTP 服务器。

结果通常为局域网 IP，并非公网出口 IP；多网卡或 VPN 环境下由系统路由决定。此方法不检测互联网是否可达。

## 开发检查

源码在 `src/`，测试在 `tests/`。测试模拟网络与邮件服务，不实际发送邮件。

```sh
python3 -m pip install ruff pytest
python3 -m pytest -q
python3 -m ruff check .
python3 -m ruff format --check .
```
