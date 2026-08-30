# IPNotifier

IPNotifier 是一个轻量级的 Python 脚本，用于获取本机局域网 IP 地址，并通过 SMTP 邮件发送通知。脚本启动后会立即发送一次 IP 信息，之后持续运行；IP 长时间无变化时，默认每 3 小时再次发送一次。

## 环境要求

- Python 3.6 或更高版本
- 能够访问 SMTP 邮件服务器
- 无需安装第三方 Python 包

## 配置邮箱

运行前，请打开 `Sender.py` 并修改 `mail_info`：

```python
mail_info = {
    'recv_address': '接收通知的邮箱地址',
    'sender_name': '用于发送通知的邮箱地址',
    'sender_pwd': '邮箱 SMTP 授权码',
    'smtp_server': 'smtp.example.com',
    'subject': '远程电脑 IP 信息已更新',
    'content': '您的 IP 信息: {}'
}
```

常见 SMTP 服务器：

| 邮箱     | SMTP 服务器    |
| -------- | -------------- |
| 163 邮箱 | `smtp.163.com` |
| QQ 邮箱  | `smtp.qq.com`  |

需要先在邮箱设置中开启 SMTP 服务。`sender_pwd` 应填写邮箱生成的 SMTP 授权码，通常不是邮箱登录密码。

> 安全提示：不要将真实邮箱密码或 SMTP 授权码提交到公开仓库。若授权码已经泄露，请立即前往邮箱设置中撤销并重新生成。

## 使用方法

在项目目录中执行：

```bash
python Sender.py
```

部分 Linux 系统需要使用：

```bash
python3 Sender.py
```

程序会在终端中输出当前 IP 和发送时间。按 `Ctrl+C` 可停止运行。

默认配置位于 `Sender.py` 底部：

```python
seconds_sleep = 5
itr = 3 * 3600 / seconds_sleep
```

- `seconds_sleep`：每次循环之间的等待秒数。
- `itr`：无变化时再次发送邮件所需的循环次数；默认约为 3 小时。
- 脚本默认在凌晨 3 点至早上 7 点之间不因 IP 变化发送邮件，但周期性发送逻辑仍可能在该时段触发。

## Windows 开机自启动

可以将启动脚本直接放入 Windows 启动文件夹，使 IPNotifier 在用户登录后自动运行。

1. 在 IPNotifier 项目目录中新建 `start_ipnotifier.bat`，内容如下，并将路径替换为项目的实际路径：

```bat
@echo off
cd /d "C:\path\to\IPNotifier"
start "" pythonw "C:\path\to\IPNotifier\Sender.py"
```

2. 按 `Win + R`，输入以下命令并回车：

```text
shell:startup
```

3. 将 `start_ipnotifier.bat` 的快捷方式放入打开的“启动”文件夹。也可以直接复制该 `.bat` 文件进去。
4. 双击 `.bat` 文件测试，确认能够正常收到通知邮件。下次登录 Windows 时，脚本就会自动启动。

如果系统找不到 Python，可运行以下命令查找 `python.exe` 的完整路径：

```powershell
where.exe python
```

然后在 `.bat` 中使用完整路径，例如：

```bat
@echo off
cd /d "C:\path\to\IPNotifier"
start "" "C:\Users\your-user\AppData\Local\Programs\Python\Python311\pythonw.exe" "C:\path\to\IPNotifier\Sender.py"
```

## Linux 开机自启动

可以使用用户自己的 crontab，在开机后自动运行脚本，无需创建 systemd 服务。

先确认 Python 和项目的绝对路径：

```bash
which python3
realpath Sender.py
```

打开 crontab：

```bash
crontab -e
```

在文件末尾添加一行，并将脚本路径替换为实际路径：

```cron
@reboot /usr/bin/python3 /home/your-user/IPNotifier/Sender.py >> /home/your-user/ipnotifier.log 2>&1
```

保存退出后即可生效。可以用下面的命令确认配置：

```bash
crontab -l
```

重启前建议先直接执行一次，确认脚本能够正常发送邮件：

```bash
/usr/bin/python3 /home/your-user/IPNotifier/Sender.py
```

程序启动后的输出和错误会写入：

```bash
tail -f /home/your-user/ipnotifier.log
```

如需取消自启动，再次运行 `crontab -e`，删除对应的 `@reboot` 行即可。

如果开机时网络初始化较慢，可以延迟 30 秒启动：

```cron
@reboot sleep 30 && /usr/bin/python3 /home/your-user/IPNotifier/Sender.py >> /home/your-user/ipnotifier.log 2>&1
```

## 常见问题

### 邮件登录失败

确认 SMTP 服务已经开启，服务器地址正确，并且使用的是 SMTP 授权码。部分邮件服务还要求配置正确的端口和 SSL/TLS；当前脚本使用普通 SMTP 连接，如服务商强制要求加密连接，需要相应调整 `Sender.py`。

### 无法获取 IP

脚本通过 UDP 路由获取本机出口对应的局域网 IP，因此机器需要存在可用的网络路由。如果开机时网络尚未连接，可在 Linux 的 `@reboot` 配置中加入启动延迟。

### 收不到邮件

检查垃圾邮件目录、接收地址和 SMTP 授权码，并先在终端前台运行脚本查看具体错误信息。
