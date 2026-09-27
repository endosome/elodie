#!/bin/sh
# Checks an image of elodie: imports a photo and a video, verifies them and
# checks the warnings of the entrypoint. Used by CI before an image is
# published.
#   docker/smoke-test.sh IMAGE [PLATFORM]
# QEMU_CPU selects the CPU which QEMU emulates for another platform, i.e.
#  cortex-a53 for ARMv8.0-A.
set -eu

image="$1"
platform="${2:+--platform $2}${QEMU_CPU:+ -e QEMU_CPU}"
repository="$(cd "$(dirname "$0")/.." && pwd)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
mkdir -p "$work/app" "$work/photos/new"
cp "$repository/elodie/tests/files/plain.jpg" "$repository/elodie/tests/files/video.mov" "$work/photos/new/"

run() {
    # shellcheck disable=SC2086
    docker run --rm $platform --user "$(id -u):$(id -g)" -e TZ=Europe/Warsaw \
        -v "$work/app:/elodie" -v "$work/photos:/photos" "$image" "$@"
}

if [ -n "${QEMU_CPU:-}" ]; then
    echo "== CPU emulated by QEMU: $QEMU_CPU"
    # shellcheck disable=SC2086
    docker run --rm $platform --entrypoint grep "$image" -m1 'CPU part' /proc/cpuinfo
fi

echo "== The time zone of a GPS position can be found"
# shellcheck disable=SC2086
docker run --rm $platform --entrypoint python "$image" -c \
    "from elodie import dates; assert dates.time_zone_at(52.23, 21.01).key == 'Europe/Warsaw'"

echo "== Import"
run import --destination /photos/library --trash /photos/new 2> "$work/warnings.txt"
test ! -s "$work/warnings.txt" || { cat "$work/warnings.txt"; exit 1; }
test -f "$work/photos/library/2015-12-Dec/Unknown Location/2015-12-05_00-59-26-plain.jpg"
# The name of the place depends on the geocoder (MapQuest or ExifTool)
test -f "$(echo "$work"/photos/library/2015-01-Jan/*/2015-01-19_12-45-11-video.mov)"
test -z "$(ls "$work/photos/new")"
test -f "$work/app/hash.json"
find "$work/photos/library" -name '*.elodie-tmp' | grep . && exit 1

echo "== Verify"
run verify

echo "== Warnings without /elodie and TZ"
# shellcheck disable=SC2086
docker run --rm $platform -v "$work/photos:/photos" "$image" \
    import --dry-run --destination /library /photos/library 2> "$work/warnings.txt" > /dev/null
grep -q '/elodie is not mounted' "$work/warnings.txt"
grep -q 'TZ is not set' "$work/warnings.txt"

echo "== OK"
