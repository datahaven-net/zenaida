#!/bin/bash

EPP_GATE_PROCESS_NAME="epp_gate.pl"
EPP_GATE_LOG_PATH="/home/zenaida/logs/gate"


echo "killing EPP gate process : `date`" >> "$EPP_GATE_LOG_PATH"
kill -9 `ps auxww | grep "$EPP_GATE_PROCESS_NAME" | grep -v grep | awk '{print $2}'`


exit 0
