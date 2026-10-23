"""无需提权，获取默认 IPv4 路由使用的本机地址。"""

import socket
import sys


def get_local_ip() -> str:
    """通过系统路由选择获取本机 IPv4 地址，不发送数据包。

    Returns:
        系统访问外部 IPv4 地址时选择的本机源地址。

    Raises:
        OSError: 无可用 IPv4 路由或无法创建套接字。
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        # 根据主机返回的ip，来确定主机真正使用网络的ip
        sock.connect(("1.1.1.1", 80))
        return str(sock.getsockname()[0])


def main() -> int:
    """输出 IP 地址，失败时输出错误并返回非零退出码。"""
    try:
        print(get_local_ip())
    except OSError as exc:
        print(f"无法获取本机 IPv4 地址：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
