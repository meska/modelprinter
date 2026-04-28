# ModelPrinter installation / Installazione

## Italiano

Questa guida installa ModelPrinter su una macchina Debian 12 o una CT Proxmox Debian 12.

### Requisiti

- Debian 12 o compatibile.
- Accesso root o sudo.
- Rete LAN con la Canon TC-20 raggiungibile via IPP/Bonjour.
- Una queue CUPS per la stampante, preferibilmente via IPP Everywhere.

### Installazione rapida

```bash
git clone https://github.com/meska/modelprinter.git /opt/modelprinter
cd /opt/modelprinter
bash scripts/install.sh
```

Lo script installa:

- Python 3 + venv
- Flask, pikepdf, Gunicorn
- CUPS e client CUPS
- avahi-daemon per discovery Bonjour/mDNS
- nginx
- servizio systemd `modelprinter`

### Configurazione

Il file principale è:

```bash
/etc/modelprinter.env
```

Variabili utili:

```env
MODELPRINTER_APP_ROOT=/opt/modelprinter
MODELPRINTER_JOB_ROOT=/var/lib/modelprinter/jobs
MODELPRINTER_MIN_STROKE_WIDTH=1
MODELPRINTER_CUPS_PRINTER=Canon_TC20
MODELPRINTER_CUPS_OPTIONS=InputSlot=MainRoll,CutMedia=Auto,sides=one-sided
MODELPRINTER_MAX_UPLOAD_MB=120
```

> Nota: il nome queue può essere `Canon_TC20`, `Canon_TC_20` o simile, in base a come CUPS l’ha creata. Verifica con `lpstat -p`.

### Configurare la Canon TC-20

Verifica che la stampante sia visibile dalla macchina:

```bash
lpinfo -v | grep -i 'Canon.*TC'
```

Esempio queue driverless IPP Everywhere:

```bash
lpadmin -p Canon_TC20 -E \
  -v 'dnssd://Canon%20TC-20._ipp._tcp.local/?uuid=00000000-0000-1000-8000-0011011029da' \
  -m everywhere

lpadmin -p Canon_TC20 \
  -o InputSlot=MainRoll \
  -o CutMedia=Auto \
  -o sides=one-sided
```

Controlla opzioni disponibili:

```bash
lpoptions -p Canon_TC20 -l
```

### Avvio e verifica

```bash
systemctl status modelprinter nginx cups
curl http://127.0.0.1/healthz
```

Se usi nginx incluso dal progetto, la webapp risponde su porta 80:

```bash
http://modelprinter.mecom.lan/
# oppure
http://IP_DELLA_MACCHINA/
```

### Aggiornamento deploy

```bash
cd /opt/modelprinter
git pull
bash scripts/install.sh
systemctl restart modelprinter
```

### Troubleshooting

Statici CSS/JS con errore `403`:

```bash
chmod 755 /opt/modelprinter
chmod -R a+rX /opt/modelprinter/static /opt/modelprinter/templates
systemctl reload nginx
```

Coda stampa:

```bash
lpstat -p
lpstat -o Canon_TC20
cancel JOB_ID
```

Log utili:

```bash
journalctl -u modelprinter -f
tail -f /var/log/nginx/error.log
tail -f /var/log/cups/error_log
```

---

## English

This guide installs ModelPrinter on Debian 12 or a Debian 12 Proxmox CT.

### Requirements

- Debian 12 or compatible.
- root or sudo access.
- LAN access to the Canon TC-20 through IPP/Bonjour.
- A CUPS printer queue, preferably IPP Everywhere / driverless.

### Quick install

```bash
git clone https://github.com/meska/modelprinter.git /opt/modelprinter
cd /opt/modelprinter
bash scripts/install.sh
```

The script installs:

- Python 3 + venv
- Flask, pikepdf, Gunicorn
- CUPS and CUPS clients
- avahi-daemon for Bonjour/mDNS discovery
- nginx
- `modelprinter` systemd service

### Configuration

Main configuration file:

```bash
/etc/modelprinter.env
```

Useful variables:

```env
MODELPRINTER_APP_ROOT=/opt/modelprinter
MODELPRINTER_JOB_ROOT=/var/lib/modelprinter/jobs
MODELPRINTER_MIN_STROKE_WIDTH=1
MODELPRINTER_CUPS_PRINTER=Canon_TC20
MODELPRINTER_CUPS_OPTIONS=InputSlot=MainRoll,CutMedia=Auto,sides=one-sided
MODELPRINTER_MAX_UPLOAD_MB=120
```

> Note: the CUPS queue may be named `Canon_TC20`, `Canon_TC_20`, or similar depending on local discovery. Check with `lpstat -p`.

### Configure the Canon TC-20

Check printer discovery from the host:

```bash
lpinfo -v | grep -i 'Canon.*TC'
```

Example driverless IPP Everywhere queue:

```bash
lpadmin -p Canon_TC20 -E \
  -v 'dnssd://Canon%20TC-20._ipp._tcp.local/?uuid=00000000-0000-1000-8000-0011011029da' \
  -m everywhere

lpadmin -p Canon_TC20 \
  -o InputSlot=MainRoll \
  -o CutMedia=Auto \
  -o sides=one-sided
```

Inspect available printer options:

```bash
lpoptions -p Canon_TC20 -l
```

### Start and verify

```bash
systemctl status modelprinter nginx cups
curl http://127.0.0.1/healthz
```

With the included nginx config, the app listens on port 80:

```bash
http://modelprinter.mecom.lan/
# or
http://MACHINE_IP/
```

### Updating an existing deploy

```bash
cd /opt/modelprinter
git pull
bash scripts/install.sh
systemctl restart modelprinter
```

### Troubleshooting

CSS/JS static files return `403`:

```bash
chmod 755 /opt/modelprinter
chmod -R a+rX /opt/modelprinter/static /opt/modelprinter/templates
systemctl reload nginx
```

Print queue:

```bash
lpstat -p
lpstat -o Canon_TC20
cancel JOB_ID
```

Useful logs:

```bash
journalctl -u modelprinter -f
tail -f /var/log/nginx/error.log
tail -f /var/log/cups/error_log
```
