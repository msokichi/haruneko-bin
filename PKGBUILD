# Maintainer: Sokichi M. <255059263+msokichi@users.noreply.github.com>
pkgname=haruneko-bin
_upstream_tag=260903T1833
_electron_version=44.1.1
_upstream_commit=f8e87b4ad2e35b2b22f88002a23006cd784e209c
pkgver=20${_upstream_tag/T/.}
pkgrel=1
pkgdesc='Manga, anime, and novel downloader (prebuilt Electron client)'
arch=('x86_64')
url='https://github.com/manga-download/haruneko'
license=('Unlicense' 'MIT' 'LicenseRef-Chromium-ThirdParty')
depends=('alsa-lib' 'at-spi2-core' 'cairo' 'dbus' 'expat' 'glib2' 'glibc' 'gtk3'
         'hicolor-icon-theme' 'libcups' 'libgcc' 'libx11' 'libxcb' 'libxcomposite'
         'libxdamage' 'libxext' 'libxfixes' 'libxkbcommon' 'libxrandr' 'mesa'
         'nspr' 'nss' 'pango' 'sh' 'systemd-libs')
makedepends=('squashfs-tools')
provides=("haruneko=$pkgver")
conflicts=('haruneko')
options=('!strip' '!debug')
_snap="$pkgname-$_upstream_tag.snap"
source=("$_snap::$url/releases/download/$_upstream_tag/hakuneko-electron-v$_electron_version-linux-x64.snap"
        "haruneko-$_upstream_tag.UNLICENSE::https://raw.githubusercontent.com/manga-download/haruneko/$_upstream_commit/UNLICENSE"
        "haruneko-$_upstream_tag.png::https://raw.githubusercontent.com/manga-download/haruneko/$_upstream_commit/app/res/darwin/app.iconset/icon_256x256.png"
        'haruneko.desktop'
        'haruneko.sh')
noextract=("$_snap")
sha256sums=('3ebdcb0c7521810bfb28f867469967163c1e4eb5e02279a8b8067d160c883d5f'
            '6b0382b16279f26ff69014300541967a356a666eb0b91b422f6862f6b7dad17e'
            'ff73807bdf7323b861da72e0b96c8bc66185dbb3294d36d491c3cc58d58272be'
            '1709976afa1033c2f243d6f655df92c8bb6722bb1769d8df28c88b6d10adeb64'
            '07c981406d7460f28e9c40d46d148f8c011621f2d4d112058b4bf695a730c720')

prepare() {
    # Select the native payload and leave out the Snap hooks and Ubuntu libraries.
    rm -rf -- "$srcdir/haruneko"
    unsquashfs -strict-errors -no-xattrs -no-progress -d "$srcdir/haruneko" "$srcdir/$_snap" \
        hakuneko-electron chrome_crashpad_handler chrome-sandbox \
        chrome_100_percent.pak chrome_200_percent.pak icudtl.dat \
        libffmpeg.so libvk_swiftshader.so libvulkan.so.1 vk_swiftshader_icd.json \
        locales resources/app resources.pak snapshot_blob.bin v8_context_snapshot.bin \
        LICENSE LICENSES.chromium.html
}

package() {
    local app="$pkgdir/opt/haruneko"
    local licenses="$pkgdir/usr/share/licenses/$pkgname"

    install -d "$pkgdir/opt"
    cp -a --no-preserve=ownership "$srcdir/haruneko" "$app"

    # Keep Chromium on the unprivileged user-namespace sandbox path.
    chmod 0755 "$app/hakuneko-electron" "$app/chrome_crashpad_handler" "$app/chrome-sandbox"
    chmod 0644 "$app/"*.pak "$app/icudtl.dat" "$app/"*.bin "$app/"*.so* "$app/vk_swiftshader_icd.json"
    find "$app/locales" "$app/resources" -type f -exec chmod 0644 {} +

    install -d "$licenses"
    install -m644 "$app/LICENSE" "$licenses/Electron-LICENSE"
    install -m644 "$app/LICENSES.chromium.html" "$licenses/LICENSES.chromium.html"
    rm "$app/LICENSE" "$app/LICENSES.chromium.html"
    install -m644 "$srcdir/haruneko-$_upstream_tag.UNLICENSE" "$licenses/UNLICENSE"
    install -m644 "$app/resources/app/node_modules/commander/LICENSE" "$licenses/commander-LICENSE"
    install -m644 "$app/resources/app/node_modules/ws/LICENSE" "$licenses/ws-LICENSE"

    install -Dm755 "$srcdir/haruneko.sh" "$pkgdir/usr/bin/haruneko"
    # Wayland uses the upstream application ID to match the desktop entry.
    install -Dm644 "$srcdir/haruneko.desktop" "$pkgdir/usr/share/applications/hakuneko-electron.desktop"
    install -Dm644 "$srcdir/haruneko-$_upstream_tag.png" "$pkgdir/usr/share/icons/hicolor/256x256/apps/haruneko.png"
}
