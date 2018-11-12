#!/bin/bash

EPP_GATE_PROCESS_NAME="epp_gate.pl"
EPP_GATE_PATH="/home/zenaida/zenaida/bin/epp_gate.pl"
EPP_REGISTRY_CREDENTIALS_PATH="/home/zenaida/keys/epp_credentials.txt"
RABBITMQ_GATE_CREDENTIALS_PATH="/home/zenaida/keys/rabbitmq_gate_credentials.txt"
EPP_GATE_LOG_PATH="/home/zenaida/logs/gate"
EPP_GATE_ERROR_LOG_PATH="/home/zenaida/logs/gate.err"

# start new process
echo "starting EPP gate process : `date`" >> "$EPP_GATE_LOG_PATH"
nohup perl "$EPP_GATE_PATH" "$EPP_REGISTRY_CREDENTIALS_PATH" "$RABBITMQ_GATE_CREDENTIALS_PATH" 1>>"$EPP_GATE_LOG_PATH" 2>>"$EPP_GATE_ERROR_LOG_PATH" &


# DONE!
echo "process started : `ps auxww | grep "$EPP_GATE_PROCESS_NAME" | grep -v grep | awk '{print $2}'`" >> "$EPP_GATE_LOG_PATH"

exit 0
