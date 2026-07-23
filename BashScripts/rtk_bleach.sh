#!/opt/bin/bash

rtk_counter="/opt/tmp/rtk_counter"
rtk_address="/opt/tmp/rtk_address"
isLock="/opt/tmp/isLock"
isLogLocal=true
max_tries=10


2log() {

# Telegram settings
BOT_TOKEN="XXXX"
GROUP_CHAT_ID="XXX"

# Sending message via Telegram bot or logger
if $isLogLocal; then
	logger -t "wan.d" -p warn "$1"
else
	curl -s -X POST "https://api.telegram.org/bot$BOT_TOKEN/sendMessage" \
		-d chat_id="$GROUP_CHAT_ID" \
		-d text="$1" >/dev/null
fi

}


if [ "$interface" == "ppp0" ] && [ $(cat $isLock) ]; then
	echo true > $isLock; [ -f "$rtk_address" ] || echo "0.0.0.0" > $rtk_address
	sleep 3; addr=$(ndmq -p "show interface PPPoE0" -P address)
	if [ "$addr" == $(cat $rtk_address) ]; then
		echo "0" > $rtk_counter
		#2log "RTK::Bleach: ✅ Public WAN IP hasn't changed!"
		sleep 2; echo false > $isLock; exit 0
	elif [ "$addr" == "" ]; then
		#2log "RTK::Bleach: ❌ PPPoE WAN IP is empty! Force reconnecting PPPoE...
		sleep 2; echo false > $isLock; exit 0
	elif echo "$addr" | grep -qE "^(10\.|100\.6[4-9]\.|100\.[7-9][0-9]\.|100\.1[01][0-9]\.|100\.12[0-7]\.|172\.1[6-9]\.|172\.2[0-9]\.|172\.3[01]\.)"; then
		[ -f "$rtk_counter" ] || echo "0" > $rtk_counter
		try_nr="$(cat $rtk_counter)"; try_nr=$((try_nr+1))
		if [ $try_nr -gt $max_tries ]; then
			2log "RTK::Bleach: ❌❌❌ Giving up to get public WAN IP!"
			sleep 2; echo false > $isLock; exit 0
		fi
		2log "RTK::Bleach: ⚫ PPPoE is up, new WAN IP is $addr! Force reconnecting PPPoE...
(try $try_nr of $max_tries)"
		echo "$try_nr" > $rtk_counter
		sleep 2; ndmq -p "interface PPPoE0 down"
		sleep 2; ndmq -p "interface PPPoE0 up"
		sleep 2; echo false > $isLock; exit 0
	else
		echo "$addr" > $rtk_address
		2log "RTK::Bleach: ⚪ Success! PPPoE is up, new WAN IP is $addr!"
		sleep 2; echo false > $isLock; exit 0
	fi
else
	exit 0; fi
