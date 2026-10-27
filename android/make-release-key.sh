#!/bin/sh
# ---------------------------------------------------------------------
# Create the one signing key this app will use for the rest of its life.
#
# READ THIS FIRST. Android identifies an app by the key that signed it.
# Every update must be signed with the SAME key, or a phone will refuse to
# install it over the copy already there - the reader has to delete the app
# and lose whatever is in it. There is no way to change the key afterwards.
# So: run this ONCE, then back up BOTH files it leaves behind, in two
# places, and never commit either of them.
# ---------------------------------------------------------------------
set -e
here=$(cd "$(dirname "$0")" && pwd)

if [ -f "$here/release.jks" ]; then
  echo "release.jks already exists. Not touching it."
  echo "If you genuinely mean to start over, move it aside first - and"
  echo "understand that every copy of the app signed with the old key can"
  echo "then never be updated again."
  exit 1
fi

if [ -z "$1" ]; then
  echo 'Usage: ./make-release-key.sh "a long passphrase you will not lose"'
  echo
  echo "Use something you can find again in five years. If you lose it the"
  echo "key is useless and the app can never be updated."
  exit 1
fi

keytool -genkeypair -v \
  -keystore "$here/release.jks" \
  -alias codex \
  -keyalg RSA -keysize 4096 \
  -validity 10950 \
  -storepass "$1" -keypass "$1" \
  -dname "CN=The Jarrell Codex, OU=Jarrell Codex, O=Jarrell Codex, C=US"

cat > "$here/keystore.properties" <<EOF
storeFile=release.jks
storePassword=$1
keyAlias=codex
keyPassword=$1
EOF

cat <<'EOF'

Done. Two files were written next to this script:
   release.jks            - the key. 30 years' validity, RSA 4096.
   keystore.properties    - where the build finds it, and the password.

BACK BOTH UP NOW, somewhere that is not this computer. Losing them means no
future version of this app can ever be installed over the one people
already have.

Then build a signed release with:
   gradle :app:assembleRelease
EOF
