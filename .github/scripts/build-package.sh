#!/usr/bin/env bash
set -euo pipefail

# Install signed repository packages before running the recipe as the builder.
mapfile -t dependencies < <(awk '
    $1 ~ /^(depends|makedepends|checkdepends)(_x86_64)?$/ && $2 == "=" { print $3 }
' /workspace/.SRCINFO)
pacman -Syu --noconfirm --needed -- desktop-file-utils namcap shellcheck \
    dbus xorg-server-xvfb xorg-xauth xorg-xwininfo "${dependencies[@]}"

id -u builder >/dev/null 2>&1 || useradd --create-home builder
cd /home/builder
cp /workspace/{PKGBUILD,.SRCINFO,haruneko.sh,haruneko.desktop} .
chown builder:builder PKGBUILD .SRCINFO haruneko.sh haruneko.desktop

shellcheck -e SC2034,SC2154 -s bash PKGBUILD
shellcheck haruneko.sh /workspace/.github/scripts/build-package.sh
desktop-file-validate haruneko.desktop
runuser -u builder -- bash -euo pipefail -c '
    makepkg --printsrcinfo | diff -u .SRCINFO -
    makepkg --verifysource
    makepkg --cleanbuild --force
'

shopt -s nullglob
packages=(haruneko-bin-*-x86_64.pkg.tar.zst)
test "${#packages[@]}" -eq 1
package=${packages[0]}

runuser -u builder -- namcap PKGBUILD "$package" | tee namcap.log
# Namcap flags prebuilt ELF files under /opt. Other errors fail the build.
if grep -Fv "haruneko-bin E: ELF files outside of a valid path ('opt/')." namcap.log |
    grep -E '^[^[:space:]]+ E:'; then
    exit 1
fi
pacman -Qip "$package"
pacman -U --noconfirm -- "$package"
pacman -Qkk haruneko-bin

for file in /opt/haruneko/{hakuneko-electron,chrome_crashpad_handler,chrome-sandbox,*.so*}; do
    links=$(ldd "$file")
    if grep -F 'not found' <<<"$links"; then
        printf 'Missing ELF dependency in %s\n' "$file" >&2
        exit 1
    fi
done
test "$(stat -c '%u:%g:%a' /opt/haruneko/chrome-sandbox)" = 0:0:755

# Use a local page to check that the renderer and preload can show a window.
cat > smoke.html <<'HTML'
<!doctype html>
<meta charset="utf-8">
<title>Haruneko CI smoke test</title>
<script>window.ipcRenderer.invoke('ApplicationWindow::ShowWindow');</script>
HTML
cd /tmp
# Expand variables inside the smoke-test shell.
# shellcheck disable=SC2016
runuser -u builder -- xvfb-run -a dbus-run-session -- timeout --kill-after=5s 30s \
    bash -euo pipefail -c '
        haruneko --ozone-platform=x11 --origin=file:///home/builder/smoke.html &
        app=$!
        trap "kill \"$app\" 2>/dev/null || true" EXIT
        for _ in {1..40}; do
            kill -0 "$app"
            if window=$(xwininfo -name "Haruneko CI smoke test" 2>/dev/null) &&
                [[ $window == *"Map State: IsViewable"* ]]; then
                printf "Haruneko displayed the smoke-test window.\n"
                exit 0
            fi
            sleep 0.5
        done
        printf "Haruneko did not display the smoke-test window.\n" >&2
        exit 1
    '

install -m644 "/home/builder/$package" /out/
