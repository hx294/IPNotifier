"""使用模拟对象验证监控逻辑，不实际联网发信。"""

from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock

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
    """执行有限轮检查，验证等待间隔并返回发信模拟对象。"""
    sender = MagicMock(side_effect=failures)
    sleeper = MagicMock(side_effect=[None] * (len(addresses) - 1) + [KeyboardInterrupt])
    monkeypatch.setattr(app, "get_local_ip", MagicMock(side_effect=addresses))
    monkeypatch.setattr(app, "send_notification", sender)
    monkeypatch.setattr(app.time, "sleep", sleeper)
    with pytest.raises(KeyboardInterrupt):
        app.monitor(config)
    assert all(call.args == (180,) for call in sleeper.call_args_list)
    return sender


def test_initial_and_unchanged_ip_do_not_notify(
    monkeypatch: pytest.MonkeyPatch, config: app.MailConfig
) -> None:
    run_checks(monkeypatch, config, ["10.0.0.1", "10.0.0.1"]).assert_not_called()


def test_changed_ip_notifies_once(
    monkeypatch: pytest.MonkeyPatch, config: app.MailConfig
) -> None:
    sender = run_checks(monkeypatch, config, ["10.0.0.1", "10.0.0.2", "10.0.0.2"])
    sender.assert_called_once_with(config, "10.0.0.1", "10.0.0.2")


def test_failed_send_retries(
    monkeypatch: pytest.MonkeyPatch, config: app.MailConfig
) -> None:
    sender = run_checks(
        monkeypatch,
        config,
        ["10.0.0.1", "10.0.0.2", "10.0.0.2"],
        [app.smtplib.SMTPException(), None],
    )
    assert sender.call_count == 2
    assert sender.call_args_list[0] == sender.call_args_list[1]


def test_network_failure_preserves_baseline(
    monkeypatch: pytest.MonkeyPatch, config: app.MailConfig
) -> None:
    sender = run_checks(
        monkeypatch, config, [OSError(), "10.0.0.1", OSError(), "10.0.0.2"]
    )
    sender.assert_called_once_with(config, "10.0.0.1", "10.0.0.2")


def test_missing_config(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="缺少配置"):
        app.load_config(tmp_path / ".env")


@pytest.mark.parametrize(
    "setting", ["SMTP_PORT=abc", "SMTP_PORT=0", "SMTP_SECURITY=plain"]
)
def test_invalid_config(tmp_path: Path, setting: str) -> None:
    path = tmp_path / ".env"
    path.write_text(app.ENV_PATH.with_name(".env.example").read_text() + "\n" + setting)
    with pytest.raises(ValueError):
        app.load_config(path)


@pytest.mark.parametrize("security", ["ssl", "starttls"])
def test_smtp_encryption_and_content(
    monkeypatch: pytest.MonkeyPatch, config: app.MailConfig, security: str
) -> None:
    config = replace(config, security=security)
    factory = MagicMock()
    monkeypatch.setattr(
        app.smtplib, "SMTP_SSL" if security == "ssl" else "SMTP", factory
    )
    app.send_notification(config, "10.0.0.1", "10.0.0.2")
    smtp = factory.return_value.__enter__.return_value
    assert smtp.starttls.call_count == (security == "starttls")
    smtp.login.assert_called_once_with("user", "secret")
    message = smtp.send_message.call_args.args[0]
    assert "10.0.0.1" in message.get_content()
    assert "10.0.0.2" in message.get_content()
    assert message["To"] == config.recipient
