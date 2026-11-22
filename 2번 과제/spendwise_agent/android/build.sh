#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
: "${ANDROID_HOME:?Android SDK is required}"
: "${SPENDWISE_KEYSTORE:?Set the path to the application signing keystore}"
: "${SPENDWISE_STORE_PASS:?Set the signing password}"
platform="$ANDROID_HOME/platforms/android-35/android.jar"
tools="$ANDROID_HOME/build-tools/35.0.0"
out="$(mktemp -d)"
trap 'rm -rf -- "$out"' EXIT
mkdir -p "$out/res/drawable-nodpi" "$out/classes" "$out/dex"
cp ../public/icon-192.png "$out/res/drawable-nodpi/spendwise.png"
"$tools/aapt2" compile --dir "$out/res" -o "$out/resources.zip"
"$tools/aapt2" link -I "$platform" --manifest AndroidManifest.xml -o "$out/base.apk" "$out/resources.zip"
javac --release 8 -encoding UTF-8 -classpath "$platform" -d "$out/classes" MainActivity.java
jar cf "$out/classes.jar" -C "$out/classes" .
"$tools/d8" --release --min-api 24 --lib "$platform" --output "$out/dex" "$out/classes.jar"
(cd "$out/dex" && zip -q "$out/base.apk" classes.dex)
"$tools/zipalign" -f 4 "$out/base.apk" "$out/aligned.apk"
"$tools/apksigner" sign --ks "$SPENDWISE_KEYSTORE" --ks-key-alias spendwise --ks-pass env:SPENDWISE_STORE_PASS \
    --v4-signing-enabled false --out "$out/SpendWise.apk" "$out/aligned.apk"
"$tools/apksigner" verify --verbose --print-certs "$out/SpendWise.apk"
"$tools/zipalign" -c 4 "$out/SpendWise.apk"
"$tools/aapt2" dump badging "$out/SpendWise.apk" | head -n 20
cp "$out/SpendWise.apk" SpendWise.apk
