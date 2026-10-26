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

## 开机自启动

先完成上面的配置并手动运行成功，再设置自启动。下面的路径均为示例，请替换为实际绝对路径；使用虚拟环境或 Conda 时，应填写该环境的 Python 路径。

### Linux：使用 crontab

适用于已安装并启用 cron/crond 服务的系统，无需登录桌面。

1. 在平时运行脚本的环境中执行 `python3 -c "import sys; print(sys.executable)"`，获取 Python 绝对路径。
2. 执行 `crontab -e`，在末尾添加一行（不要覆盖已有内容）：

   ```cron
   @reboot /绝对路径/python3 /绝对路径/IPNotifier/src/ip_notifier.py >> "$HOME/ipnotifier.log" 2>&1
   ```

   路径含空格时，用双引号包住对应路径。
3. 保存后执行 `crontab -l` 确认配置，重启后用 `tail -n 30 ~/ipnotifier.log` 查看运行日志。

取消自启动：执行 `crontab -e` 删除这一行，下次开机生效。此方式只在启动时运行一次，不会自动重启意外退出的脚本。`@reboot` 的说明见 [crontab 手册](https://man7.org/linux/man-pages/man5/crontab.5.html)。

### Windows：将 bat 脚本放入启动目录

此方法无需管理员权限，当前用户登录 Windows 后自动运行；仅开机但未登录时不会运行。

1. 在能运行脚本的终端中执行 `python -c "import sys; print(sys.executable)"`，记下 Python 绝对路径。
2. 新建 `IPNotifier.bat`，填写以下内容，将两处路径替换为实际路径：

   ```bat
   @echo off
   "C:\Python313\python.exe" "C:\IPNotifier\src\ip_notifier.py"
   pause
   ```

   保存时选择“所有文件”，确保文件名不是 `IPNotifier.bat.txt`。`pause` 方便程序退出后查看错误信息。
3. 双击 bat 文件确认能运行，再按 `Ctrl+C` 停止测试运行，避免重复启动。
4. 按 `Win+R`，输入 `shell:startup` 并回车，将 bat 文件放入打开的目录。以后登录时便会自动运行。

运行时会保留命令窗口，可最小化；关闭窗口会停止监控。取消自启动时，从启动目录删除 bat 文件即可。启动目录说明见 [微软文档](https://support.microsoft.com/en-au/windows/experience/startup-boot/configure-startup-applications-in-windows)。

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
