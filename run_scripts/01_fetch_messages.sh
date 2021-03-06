#!/usr/bin/env bash

set -e

if [ $# -ne 5 ]; then
    echo "Usage: sh 01_fetch_messages.sh <user> <rapid-pro-root> <rapid-pro-server> <rapid-pro-token> <data-root>"
    echo "Downloads radio show answers from each show"
    exit
fi

USER=$1
RP_DIR=$2
RP_SERVER=$3
RP_TOKEN=$4
DATA_ROOT=$5

TEST_CONTACTS_PATH="$(pwd)/test_contacts.json"

cd "$RP_DIR/fetch_runs"

mkdir -p "$DATA_ROOT/01 Raw Messages"

SHOWS=(
    "esc4jmcna_activation"
    )

for SHOW in ${SHOWS[@]}
do
    echo "Exporting show $SHOW"

    sh docker-run.sh --flow-name "$SHOW" --test-contacts-path "$TEST_CONTACTS_PATH" \
        "$RP_SERVER" "$RP_TOKEN" "$USER" all \
        "$DATA_ROOT/00 UUIDs/phone_uuids.json" "$DATA_ROOT/01 Raw Messages/$SHOW.json"
done
