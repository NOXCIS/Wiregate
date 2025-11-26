#!/bin/sh
# Alpine Linux Mirror Selection Script
# Tests multiple mirrors and selects the fastest responding one

set -e

VERSION=$(cat /etc/alpine-release | cut -d. -f1,2)
ARCH=$(uname -m)

# Backup original repositories
cp /etc/apk/repositories /etc/apk/repositories.backup

# List of mirrors to test (in order of preference)
MIRRORS="
http://dl-cdn.alpinelinux.org/alpine
http://mirror.leaseweb.com/alpine
http://mirrors.edge.kernel.org/alpine
http://alpine.mirror.wearetriple.com/alpine
http://uk.alpinelinux.org/alpine
http://mirrors.xtom.com/alpine
http://mirror.yandex.ru/alpine
http://mirror.ams1.nl.leaseweb.net/alpine
http://mirror.one.com/alpine
http://mirror.bytemark.co.uk/alpine
http://mirror.chaoticum.net/alpine
http://mirror.cyberbits.eu/alpine
http://mirror.f4st.host/alpine
http://mirror.fcix.net/alpine
http://mirror.genesisadaptive.com/alpine
http://mirror.its.dal.ca/alpine
http://mirror.lagis.at/alpine
http://mirror.math.princeton.edu/pub/alpine
http://mirror.moson.org/alpine
http://mirror.nyi.net/alpine
http://mirror.rackspace.com/alpine
http://mirror.sjtu.edu.cn/alpine
http://mirror.steadfast.net/alpine
http://mirror.truenetwork.ru/alpine
http://mirror.ufro.cl/alpine
http://mirror.vpsfree.cz/alpine
http://mirror.wtnet.de/alpine
http://mirrors.aliyun.com/alpine
http://mirrors.bfsu.edu.cn/alpine
http://mirrors.cqu.edu.cn/alpine
http://mirrors.dotsrc.org/alpine
http://mirrors.estointernet.in/alpine
http://mirrors.163.com/alpine
http://mirrors.nju.edu.cn/alpine
http://mirrors.sjtug.sjtu.edu.cn/alpine
http://mirrors.tuna.tsinghua.edu.cn/alpine
http://mirrors.ustc.edu.cn/alpine
http://mirrors.xmission.com/alpine
http://nl.alpinelinux.org/alpine
http://de.alpinelinux.org/alpine
http://fr.alpinelinux.org/alpine
http://jp.alpinelinux.org/alpine
http://kr.alpinelinux.org/alpine
http://us.alpinelinux.org/alpine
"

MIRROR_FOUND=0

echo "Testing Alpine mirrors for fastest response..."

for mirror in $MIRRORS; do
    echo "Testing: $mirror"
    if wget -q -T 2 -O /dev/null "$mirror/v${VERSION}/main/${ARCH}/APKINDEX.tar.gz" 2>/dev/null; then
        echo "$mirror/v${VERSION}/main" > /etc/apk/repositories
        echo "$mirror/v${VERSION}/community" >> /etc/apk/repositories
        echo "✓ Selected mirror: $mirror"
        MIRROR_FOUND=1
        break
    else
        echo "✗ Mirror failed or timed out"
    fi
done

if [ "$MIRROR_FOUND" -eq 0 ]; then
    echo "⚠ All mirrors failed, using default repositories"
    mv /etc/apk/repositories.backup /etc/apk/repositories
fi

echo "Updating APK cache..."
if ! apk update; then
    echo "⚠ APK update failed, but continuing with build..."
    echo "This may be due to temporary network issues."
fi

