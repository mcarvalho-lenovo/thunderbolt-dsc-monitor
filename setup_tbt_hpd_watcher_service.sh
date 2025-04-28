#!/usr/bin/env bash

set -e

SERVICE_NAME="tbt-watcher"
PY_SCRIPT_NAME="tbt_wacther.py"
DSC_SCRIPT_NAME="dsc.py"
UNIT_FILE="${SERVICE_NAME}.service"

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run this script as root (e.g., sudo ./setup_tbt_hpd_watcher_service.sh)."
  exit 1
fi

echo "==> Installing Python3, pip, and pyudev..."
apt-get update -y
apt-get install -y python3 python3-pip
pip3 install pyudev

INSTALL_DIR="/opt/tbt-monitor"
mkdir -p "$INSTALL_DIR"

echo "==> Copying Python scripts to $INSTALL_DIR"
cp "$PY_SCRIPT_NAME" "$INSTALL_DIR/"
cp "$DSC_SCRIPT_NAME" "$INSTALL_DIR/"

chmod +x "${INSTALL_DIR}/${PY_SCRIPT_NAME}"
chmod +x "${INSTALL_DIR}/${DSC_SCRIPT_NAME}"

# Create the systemd service
cat << EOF > "/etc/systemd/system/${UNIT_FILE}"
[Unit]
Description=Monitor Thunderbolt Hot-Plug Events
After=network.target

[Service]
ExecStart=/usr/bin/python3 ${INSTALL_DIR}/${PY_SCRIPT_NAME}
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo "==> Enabling and starting the ${SERVICE_NAME} service..."
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl start "${SERVICE_NAME}"

PACKAGE_NAME="tbt_monitor_package.tar.gz"
echo "==> Creating a tar.gz package of the installed files: ${PACKAGE_NAME}"

tar -czf "${PACKAGE_NAME}" \
  -C "${INSTALL_DIR}" "${PY_SCRIPT_NAME}" "${DSC_SCRIPT_NAME}" \
  -C "/etc/systemd/system" "${UNIT_FILE}"

echo "==> Installation complete."
echo "------------------------------------------------------------------"
echo "Systemd service: /etc/systemd/system/${UNIT_FILE}"
echo "Python scripts:  ${INSTALL_DIR}/${PY_SCRIPT_NAME}, ${INSTALL_DIR}/${DSC_SCRIPT_NAME}"
echo "Package created: ${PACKAGE_NAME}"
echo "------------------------------------------------------------------"
echo "Service status:"
systemctl status "${SERVICE_NAME}" --no-pager || true
echo "------------------------------------------------------------------"
echo "To stop the service:   sudo systemctl stop ${SERVICE_NAME}"
echo "To disable the service: sudo systemctl disable ${SERVICE_NAME}"
echo "------------------------------------------------------------------"
