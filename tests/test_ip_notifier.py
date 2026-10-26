"""使用模拟对象验证监控逻辑，不实际联网发信。"""

from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from src import ip_notifier as app


@pytest.fixture
def config() -> app.MailConfig:
    """提供测试用 SMTP 配置。"""
    return app.MailConfig(
        "smtp.example.com",
        465,
        "user",
        "secret",
        "a@example.com",
        "b@example.com",
        "ssl",
    )


def run_checks(
    monkeypatch: pytest.MonkeyPatch,
    config: app.MailConfig,
    addresses: list,
    failures: list = None,
) -> MagicMock:
    """执行有限轮检查，验证等待间隔并返回发信模拟对象。

    Args:
        monkeypatch: 用于替换网络访问、发信和等待操作的 pytest fixture。
        config: 传给监控函数的邮件配置。
        addresses: 每轮获取 IP 时依次返回的地址或抛出的异常。
        failures: 每次发信的模拟结果；列表中的异常会被抛出，None 表示成功。

    Returns:
        记录发信调用参数和次数的模拟对象。
    """
    sender = MagicMock(side_effect=failures)
    # 最后一轮等待时中断无限监控循环，避免测试实际等待或持续运行。
    sleeper = MagicMock(side_effect=[None] * (len(addresses) - 1) + [KeyboardInterrupt])
    monkeypatch.setattr(app, "get_local_ip", MagicMock(side_effect=addresses))
    monkeypatch.setattr(app, "send_notification", sender)
    monkeypatch.setattr(app.time, "sleep", sleeper)
    with pytest.raises(KeyboardInterrupt):
        app.monitor(config)
    # 即使获取 IP 或发信失败，每轮检查也应保持 180 秒的等待间隔。
    assert all(call.args == (180,) for call in sleeper.call_args_list)
    return sender


def test_initial_ip_notifies_once_and_unchanged_ip_does_not_repeat(
    monkeypatch: pytest.MonkeyPatch, config: app.MailConfig
) -> None:
    """首次获取 IP 时发送通知，后续地址不变时不重复发送。"""
    sender = run_checks(monkeypatch, config, ["10.0.0.1", "10.0.0.1"])
    sender.assert_called_once_with(config, None, "10.0.0.1")


def test_changed_ip_notifies_once(
    monkeypatch: pytest.MonkeyPatch, config: app.MailConfig
) -> None:
    """初始通知后，IP 变化仅触发一次额外通知。"""
    sender = run_checks(monkeypatch, config, ["10.0.0.1", "10.0.0.2", "10.0.0.2"])
    assert sender.call_args_list == [
        call(config, None, "10.0.0.1"),
        call(config, "10.0.0.1", "10.0.0.2"),
    ]


def test_failed_change_notification_retries(
    monkeypatch: pytest.MonkeyPatch, config: app.MailConfig
) -> None:
    """变更通知失败后保留旧 IP，在下一轮重试同一变更。"""
    sender = run_checks(
        monkeypatch,
        config,
        ["10.0.0.1", "10.0.0.2", "10.0.0.2"],
        # 初始通知成功，首次变更通知失败，下一轮重试成功。
        [None, app.smtplib.SMTPException(), None],
    )
    assert sender.call_args_list == [
        call(config, None, "10.0.0.1"),
        call(config, "10.0.0.1", "10.0.0.2"),
        call(config, "10.0.0.1", "10.0.0.2"),
    ]


def test_network_failure_preserves_baseline(
    monkeypatch: pytest.MonkeyPatch, config: app.MailConfig
) -> None:
    """获取 IP 失败既不建立初始基准，也不覆盖已有基准。"""
    sender = run_checks(
        monkeypatch, config, [OSError(), "10.0.0.1", OSError(), "10.0.0.2"]
    )
    assert sender.call_args_list == [
        call(config, None, "10.0.0.1"),
        call(config, "10.0.0.1", "10.0.0.2"),
    ]


def test_missing_config(tmp_path: Path) -> None:
    """配置文件不存在时，应明确报告缺少必需配置。"""
    # 内部代码必须抛出异常
    with pytest.raises(ValueError, match="缺少配置"):
        app.load_config(tmp_path / ".env")


@pytest.mark.parametrize(
    "setting", ["SMTP_PORT=abc", "SMTP_PORT=0", "SMTP_SECURITY=plain"]
)
def test_invalid_config(tmp_path: Path, setting: str) -> None:
    """非数字端口、无效端口及不支持的加密方式均应被拒绝。"""
    path = tmp_path / ".env"
    # 在示例配置末尾覆盖单个字段，确保测试只针对当前参数化的无效值。
    path.write_text(app.ENV_PATH.with_name(".env.example").read_text() + "\n" + setting)
    with pytest.raises(ValueError):
        app.load_config(path)


@pytest.mark.parametrize("security", ["ssl", "starttls"])
def test_smtp_encryption_and_content(
    monkeypatch: pytest.MonkeyPatch, config: app.MailConfig, security: str
) -> None:
    """验证两种 SMTP 加密方式、登录凭据及通知邮件的地址信息。"""
    config = replace(config, security=security)
    factory = MagicMock()
    monkeypatch.setattr(
        app.smtplib, "SMTP_SSL" if security == "ssl" else "SMTP", factory
    )
    app.send_notification(config, "10.0.0.1", "10.0.0.2")
    # with 语句实际使用的是 SMTP 工厂返回对象的 __enter__ 返回值。
    smtp = factory.return_value.__enter__.return_value
    # SSL 连接无需再次升级加密；普通 SMTP 连接应调用一次 starttls。
    assert smtp.starttls.call_count == (security == "starttls")
    smtp.login.assert_called_once_with("user", "secret")
    message = smtp.send_message.call_args.args[0]
    assert "10.0.0.1" in message.get_content()
    assert "10.0.0.2" in message.get_content()
    assert message["To"] == config.recipient
