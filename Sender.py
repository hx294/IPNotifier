# coding: utf-8

import smtplib
import time
import datetime
from email.mime.text import MIMEText
from email.header import Header
import socket

_local_ip = None

mail_info = {
    'recv_address': 'recv_mail', #你的接收端邮箱地址
    'sender_name': 'send_mail', #你的发送端邮箱地址
    'sender_pwd': 'authenticationcode', #授权码（用于qq或163邮箱）
    'smtp_server': 'smtp.123.com', #smtp发送服务器（在邮箱帮助页面查看）
    'subject': '远程电脑IP信息已更新',
    'content': '您的校内网IP信息: {}'
}


def send_message(content):
    # 设置发送邮件的内容
    msg = MIMEText(content, 'plain', 'utf-8')
    msg['From'] = Header(mail_info.get('sender_name'))
    msg['Subject'] = Header(mail_info.get('subject'), 'utf-8')
    msg['To'] = Header(mail_info.get('recv_address'))
    # 发送邮件
    smtp = smtplib.SMTP()
    smtp.connect(mail_info['smtp_server'])
    smtp.login(mail_info['sender_name'], mail_info['sender_pwd'])
    smtp.sendmail(mail_info['sender_name'], mail_info['recv_address'],msg.as_string())
    try:
        smtp.quit()
    except smtplib.SMTPException as e:
        e = "Failed to close SMTP session."


def get_host_ip():
    """
    这个方法是目前见过最优雅获取本机服务器的IP方法了。没有任何的依赖，也没有去猜测机器上的网络设备信息。
    而且是利用 UDP 协议来实现的，生成一个UDP包，把自己的 IP 放如到 UDP 协议头中，然后从UDP包中获取本机的IP。
    这个方法并不会真实的向外部发包，所以用抓包工具是看不到的。但是会申请一个 UDP 的端口，所以如果经常调用也会比较耗时的，这里如果需要可以将查询到的IP给缓存起来，性能可以获得很大提升。
    :return:
    """
    global _local_ip
    s = None
    try:
        if not _local_ip:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            _local_ip = s.getsockname()[0]
        return _local_ip
    finally:
        if s:
            s.close()


def mail_ip_send(ip_real):
    """
    使用邮件发送IP地址.
    """
    info_dict = "校内网IP: " + ip_real + "\n" + datetime.datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S %Z") + "\n"
    print(info_dict)
    send_message(info_dict)


ip_val = get_host_ip()
num = 0
seconds_sleep = 5  # 检测IP地址的时间间隔
itr = 3 * 3600 / seconds_sleep  # IP地址无变动时默认发送邮件的小时数
while 1:
    ip_real = get_host_ip()
    h = datetime.datetime.now().hour
    if (ip_real != ip_val) & ((h <= 3) | (h >= 7)) | num == 0:  #晚上3点到早7点之间不发送IP
        mail_ip_send(ip_real)
        ip_val = ip_real
    num += 1
    if num >= itr:
        mail_ip_send(ip_real)
        ip_val = ip_real
        num = 0
    time.sleep(seconds_sleep)
