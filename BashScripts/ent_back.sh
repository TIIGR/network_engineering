#!/bin/sh

# Telegram settings
BOT_TOKEN="XXXX"
GROUP_CHAT_ID="XXX"

# Router settings
ROUTER_NAME="Keen-Pro100net-Serv"

# Backup settings
BACKUP_FILE="/opt/ent_backup/opkg_backup_${ROUTER_NAME}_$(date +%Y%m%d).tar.gz"
BACKUP_DIR="/opt"
#LOG_FILE="/opt/ent_backup/backup_log.log"

log() {
    logger -t "ent_backup" -p "$1" "$2"
}

# Start backup
log warn "Starting backup creation"

sh -c 'echo 3 > /proc/sys/vm/drop_caches'

# Create backup
if tar czf "$BACKUP_FILE" -C "$BACKUP_DIR" . 2>/dev/null; then
    if [ -f "$BACKUP_FILE" ]; then
        FILE_SIZE=$(wc -c < "$BACKUP_FILE")
        FILE_SIZE_MB=$((FILE_SIZE / 1024 / 1024))
        log warn "Backup created: $BACKUP_FILE (${FILE_SIZE_MB} MB)"
    else
        log err "Error: Backup file not found after creation"
        exit 0
    fi
else
    log err "Error while creating backup"
    exit 0
fi

# Check file size
MAX_SIZE_MB=50
if [ $FILE_SIZE_MB -gt $MAX_SIZE_MB ]; then
    log warn "Backup is too large: ${FILE_SIZE_MB} MB > ${MAX_SIZE_MB} MB"
    curl -s -X POST "https://api.telegram.org/bot$BOT_TOKEN/sendMessage" \
        -d chat_id="$GROUP_CHAT_ID" \
        -d text="❌ Backup not sent: size ${FILE_SIZE_MB}MB exceeds ${MAX_SIZE_MB}MB limit
You can download backup directly via SFTP!" >/dev/null
    exit 0
fi

# Send to Telegram
RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot$BOT_TOKEN/sendDocument" \
    -F chat_id="$GROUP_CHAT_ID" \
    -F document=@"$BACKUP_FILE" \
    -F caption="✅ Entware backup from $(date '+%d.%m.%Y')")

# Check send result
if echo "$RESPONSE" | grep -q '"ok":true'; then
    log warn "Backup successfully sent to Telegram"
    rm -f "$BACKUP_FILE"
else
    log err "Error sending backup to Telegram: $RESPONSE"
fi

exit 0
