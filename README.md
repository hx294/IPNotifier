# IPNotifier

快速获取当前默认网络使用的本机 IPv4 地址。使用 Python 3.9+ 标准库，无运行依赖，无需管理员权限。

## 运行

在仓库根目录执行：

```sh
python3 src/ip_notifier.py
```

成功时仅输出 IP 地址，便于其他脚本读取；失败时向标准错误输出原因，退出码为 `1`。

## 原理与范围

通过 UDP 套接字的 `connect()` 让操作系统选择访问 `1.1.1.1` 的路由，再读取本机源地址。程序不发送应用数据包，无需 DNS 查询或等待远端响应。

输出的是本机接口地址，通常为局域网 IP，不是通过公网服务查询到的出口 IP。多网卡或 VPN 环境下，结果由系统路由决定；仅有 IPv6 或没有可用 IPv4 路由时会失败。此方法不检测互联网是否可达。

## 开发检查

可选安装 Ruff：`python3 -m pip install ruff`。

```sh
python3 -m ruff check .
python3 -m ruff format --check .
```

源码位于 `src/`，采用 PEP 8、类型注解和 Google 风格文档字符串。
