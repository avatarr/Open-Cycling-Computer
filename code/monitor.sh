#!/bin/bash

LAST_LOG=$(ls -1r log/debug.* | head -n1)
head -n1 $LAST_LOG && tail -f $LAST_LOG
