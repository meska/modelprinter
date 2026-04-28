#!/usr/bin/env bash
set -euo pipefail

APP_USER="modelprinter"
APP_DIR="/opt/modelprinter"
JOB_DIR="/var/lib/modelprinter/jobs"
PRINTER_NAME="${MODELPRINTER_CUPS_PRINTER:-Canon_TC20}"

apt-get update
apt-get install -y python3 python3-venv python3-pip cups cups-client cups-bsd avahi-daemon printer-driver-cups-pdf nginx

id "${APP_USER}" >/dev/null 2>&1 || useradd --system --home "${APP_DIR}" --shell /usr/sbin/nologin "${APP_USER}"
mkdir -p "${APP_DIR}" "${JOB_DIR}"
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}" "${JOB_DIR}"
chmod 755 "${APP_DIR}"
chmod -R a+rX "${APP_DIR}/static" "${APP_DIR}/templates" 2>/dev/null || true

cd "${APP_DIR}"
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install flask pikepdf gunicorn

install -m 0644 deploy/modelprinter.env /etc/modelprinter.env
sed -i "s/^MODELPRINTER_CUPS_PRINTER=.*/MODELPRINTER_CUPS_PRINTER=${PRINTER_NAME}/" /etc/modelprinter.env
install -m 0644 deploy/modelprinter.service /etc/systemd/system/modelprinter.service
install -m 0644 deploy/nginx.conf /etc/nginx/sites-available/modelprinter
ln -sf /etc/nginx/sites-available/modelprinter /etc/nginx/sites-enabled/modelprinter
rm -f /etc/nginx/sites-enabled/default

systemctl enable --now cups avahi-daemon
if lpinfo -v | grep -q 'Canon%20TC-20'; then
  lpadmin -p "${PRINTER_NAME}" -E \
    -v "dnssd://Canon%20TC-20._ipp._tcp.local/?uuid=00000000-0000-1000-8000-0011011029da" \
    -m everywhere
  lpadmin -p "${PRINTER_NAME}" -o InputSlot=MainRoll -o CutMedia=Auto -o sides=one-sided
fi
systemctl daemon-reload
systemctl enable --now modelprinter
nginx -t
systemctl reload nginx
