#!/bin/bash

EPP_GATE_PROCESS_NAME="epp_gate.pl"
EPP_GATE_PATH="/home/zenaida/zenaida/bin/epp_gate.pl"
EPP_REGISTRY_CREDENTIALS_PATH="/home/zenaida/keys/epp_credentials.txt"
RABBITMQ_GATE_CREDENTIALS_PATH="/home/zenaida/keys/rabbitmq_gate_credentials.txt"
EPP_GATE_LOG_PATH="/tmp/gate"
EPP_GATE_ERROR_LOG_PATH="/tmp/gate.err"
EPP_GATE_MAX_LOG_SIZE=1000000


# rotate logs

current_log_size=`du -b "$EPP_GATE_LOG_PATH" | tr -s '\t' ' ' | cut -d' ' -f1`
# if log file size is not too big, do not need to rotate 
if [ $current_log_size -gt $MaxFileSize ]; then
    savelog -n -c 7 "$EPP_GATE_LOG_PATH"
fi



# kill existing process

echo "killing EPP gate process : `date`" >> "$EPP_GATE_LOG_PATH"

kill -9 `ps auxww | grep "$EPP_GATE_PROCESS_NAME" | grep -v grep | awk '{print $2}'`
sleep 1



# start new process

echo "starting EPP gate process : `date`" >> "$EPP_GATE_LOG_PATH"

nohup perl "$EPP_GATE_PATH" "$EPP_REGISTRY_CREDENTIALS_PATH" "$RABBITMQ_GATE_CREDENTIALS_PATH" 1>>"$EPP_GATE_LOG_PATH" 2>>"$EPP_GATE_ERROR_LOG_PATH" &

exit 0
