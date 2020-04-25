#!/usr/bin/env python3

import json
import re
import smtplib
import subprocess
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import urllib3

# Modify values. ##############################################################
api_url = "https://api.ipify.org"
fqdn = ""  # FQDN
auth_email = ""  # Cloudflare API account
auth_key = ""  # Cloudflare API key
s_acct = ""  # Gmail account
s_passwd = ""  # Gmail password
t_mail = ""  # Send to mail address
###############################################################################


def get_ip(api_url):
    http = urllib3.PoolManager()

    try:
        r = http.request('GET', api_url)
    except Exception as e:
        print("IPIFY request fail.")
        print("Error message: ", e)
        exit(99)
    ip_a = r.data.decode('utf-8')

    try:
        ip_g = subprocess.getoutput(
            "dig TXT +short o-o.myaddr.l.google.com @ns3.google.com")
    except Exception as e:
        print("Google DNS request fail.")
        print("Error message: ", e)
        exit(99)

    try:
        ip_o = subprocess.getoutput(
            "dig A +short myip.opendns.com @resolver3.opendns.com")
    except Exception as e:
        print("OpenDNS DNS request fail.")
        print("Error message: ", e)
        exit(99)

    ip_a = ip_a.replace("\n", "").replace(
        "\'", "").replace("\"", "").replace(" ", "")
    ip_g = ip_g.replace("\n", "").replace(
        "\'", "").replace("\"", "").replace(" ", "")
    ip_o = ip_o.replace("\n", "").replace(
        "\'", "").replace("\"", "").replace(" ", "")
    new_ip = {'a': ip_a, 'g': ip_g, 'o': ip_o}
    return new_ip


def send_mail(s_acct, s_passwd, t_mail, a, g, o):
    email_content = MIMEMultipart()
    email_content["subject"] = "My dynamic IP"
    email_content["from"] = s_acct
    email_content["to"] = t_mail
    msg = "API request IP: %s\nGoogle request IP: %s\nOpenDNS request IP: %s" \
        % (a, g, o)
    email_content.attach(MIMEText(msg))
    with smtplib.SMTP(host="smtp.gmail.com", port="587") as smtp:
        try:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(s_acct, s_passwd)
            smtp.send_message(email_content)
            print("Send new IP to your mail box.")
        except Exception as e:
            print("Error message: ", e)
            exit(99)


def update_hostname(url, fqdn, h, b, f):
    http = urllib3.PoolManager()

    try:
        r = http.request('GET', url, headers=h)
    except Exception as e:
        print("Error message: ", e)
        exit(99)

    d = json.loads(r.data.decode('utf-8'))

    if d['success']:
        i = 0
        while i < len(d['result']):
            n = len(d['result'][i]['name'])
            if d['result'][i]['name'] == fqdn[-n:]:
                zone_id = d['result'][i]['id']
            i += 1
    else:
        print("Connect Cloudfalre error or authentication failed.")
        exit(99)

    url = "%s/%s/dns_records" % (url, zone_id)

    try:
        r = http.request('GET', url, headers=h, fields=f)
    except Exception as e:
        print("Error message: ", e)
        exit(99)

    d = json.loads(r.data.decode('utf-8'))

    if d['result']:
        records_id = d['result'][0]['id']
        url = "%s/%s" % (url, records_id)
        try:
            r = http.request('PUT', url, headers=h, body=b)
        except Exception as e:
            print("Error message: ", e)
        d = json.loads(r.data.decode('utf-8'))
        print(d)
    else:
        try:
            r = http.request('POST', url, headers=h, body=b)
        except Exception as e:
            print("Error message: ", e)
        d = json.loads(r.data.decode('utf-8'))
        print(d)


def main():
    old_ip = subprocess.getoutput(
        "dig A +short %s @1.1.1.1" % (fqdn))
    old_ip = old_ip.replace("\n", "").replace(
        "\'", "").replace("\"", "").replace(" ", "")
    ip = get_ip(api_url)
    a, g, o = ip['a'], ip['g'], ip['o']

    if a == g and g == o:
        new_ip = a
        if old_ip == new_ip:
            print("No need to modify.")
            exit(0)
        else:
            url = "https://api.cloudflare.com/client/v4/zones"
            h = {'X-Auth-Email': auth_email, 'X-Auth-Key': auth_key,
                 'Content-Type': 'application/json'}
            b = {'type': 'A', 'name': fqdn, 'content': new_ip, 'ttl': 1}
            b = json.dumps(b).encode('utf-8')
            f = {'name': fqdn}
            update_hostname(url, fqdn, h, b, f)
    else:
        if s_acct and s_passwd and t_mail:
            send_mail(s_acct, s_passwd, t_mail, a, g, o)


if __name__ == '__main__':
    main()
