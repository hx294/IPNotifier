"""每三分钟检查本机 IPv4 地址，变化时通过 SMTP 发信。"""

import logging
import smtplib
import socket
import ssl
import sys
import time
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path

from dotenv import dotenv_values

CHECK_INTERVAL = 180
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


@dataclass(frozen=True)
class MailConfig:
    """SMTP 连接与邮件收发配置。"""

    host: str
    port: int
    username: str
    password: str
    sender: str
    recipient: str
    security: str


def load_config(path: Path = ENV_PATH) -> MailConfig:
    """读取 .env；缺少配置或值无效时抛出 ValueError。"""
    values = dotenv_values(path, interpolate=False)
    required = (
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USERNAME",
        "SMTP_PASSWORD",
        "MAIL_FROM",
        "MAIL_TO",
        "SMTP_SECURITY",
    )
    missing = [key for key in required if not values.get(key)]
    if missing:
        raise ValueError(f".env 缺少配置：{', '.join(missing)}")
    config = {key: str(values[key]) for key in required}
    try:
        port = int(config["SMTP_PORT"])
    except ValueError:
        raise ValueError("SMTP_PORT 必须是整数") from None
    if not 1 <= port <= 65535:
        raise ValueError("SMTP_PORT 必须介于 1 和 65535 之间")
    security = config["SMTP_SECURITY"].lower()
    if security not in {"ssl", "starttls"}:
        raise ValueError("SMTP_SECURITY 必须是 ssl 或 starttls")
    for key in ("MAIL_FROM", "MAIL_TO"):
        if "\r" in config[key] or "\n" in config[key]:
            raise ValueError(f"{key} 不允许包含换行符")
    return MailConfig(
        config["SMTP_HOST"],
        port,
        config["SMTP_USERNAME"],
        config["SMTP_PASSWORD"],
        config["MAIL_FROM"],
        config["MAIL_TO"],
        security,
    )


def get_local_ip() -> str:
    """通过系统路由选择获取本机 IPv4 地址，不发送数据包。

    Returns:
        系统访问外部 IPv4 地址时选择的本机源地址。

    Raises:
        OSError: 无可用 IPv4 路由或无法创建套接字。
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.connect(("1.1.1.1", 80))
        return str(sock.getsockname()[0])


def send_notification(config: MailConfig, old_ip: str, new_ip: str) -> None:
    """通过加密 SMTP 发送新旧 IP，连接或发信失败时抛出异常。"""
    message = EmailMessage()
    message["Subject"] = f"IPNotifier：本机 IP 已变更为 {new_ip}"
    message["From"] = config.sender
    message["To"] = config.recipient
    message.set_content(f"本机 IPv4 地址发生变化。\n原 IP：{old_ip}\n新 IP：{new_ip}\n")
    context = ssl.create_default_context()
    if config.security == "ssl":
        connection = smtplib.SMTP_SSL(
            config.host, config.port, timeout=15, context=context
        )
    else:
        connection = smtplib.SMTP(config.host, config.port, timeout=15)
    with connection as smtp:
        if config.security == "starttls":
            smtp.starttls(context=context)
        smtp.login(config.username, config.password)
        smtp.send_message(message)


def monitor(config: MailConfig) -> None:
    """首次建立基线；IP 变化时发信，失败后下轮重试。"""
    previous_ip = None
    while True:
        try:
            current_ip = get_local_ip()
        except OSError:
            logging.warning("无法获取本机 IPv4 地址，三分钟后重试")
        else:
            if current_ip != previous_ip:
                try:
                    send_notification(config, previous_ip, current_ip)
                except (OSError, smtplib.SMTPException):
                    logging.warning(
                        "邮件发送失败，请检查网络和 SMTP 配置；三分钟后重试"
                    )
                else:
                    logging.info("已通知 IP 变更：%s -> %s", previous_ip, current_ip)
                    previous_ip = current_ip
            if previous_ip is None:
                previous_ip = current_ip
                logging.info("初始 IP：%s", current_ip)
        time.sleep(CHECK_INTERVAL)


def main() -> int:
    """加载配置并启动监控，按 Ctrl+C 正常退出。"""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    try:
        config = load_config()
    except (OSError, ValueError) as exc:
        logging.error("配置加载失败：%s", exc)
        return 1
    try:
        monitor(config)
    except KeyboardInterrupt:
        logging.info("监控已停止")
    return 0


if __name__ == "__main__":
    sys.exit(main())
