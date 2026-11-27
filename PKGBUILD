# Maintainer: msokichi <msokichi@example.com>
pkgname=haruneko-bin
pkgver=44.1.1
pkgrel=1
pkgdesc="Manga, Anime & Novel Downloader (Electron, repackaged from upstream snap)"
arch=('x86_64')
url="https://github.com/manga-download/haruneko"
license=('MIT')
depends=('gtk3' 'nss' 'alsa-lib' 'libxss' 'libnotify')
makedepends=('squashfs-tools')
options=('!strip')
_upstream_tag=260903T1833
source=(
    "https://github.com/manga-download/haruneko/releases/download/${_upstream_tag}/hakuneko-electron-v${pkgver}-linux-x64.snap"
    "haruneko.desktop"
    "haruneko.sh"
)
sha256sums=(
    '3ebdcb0c7521810bfb28f867469967163c1e4eb5e02279a8b8067d160c883d5f'
    'f27c2f17e027490b17605653685feb549c862a858217038d613379ac2f9e5204'
    '585aa7df3e91086e13ad8a739045b040c786321748211c037bca6236003c762e'
)

prepare() {
    cd "${srcdir}"
    rm -rf snap
    unsquashfs -q -d "${srcdir}/snap" "${srcdir}"/*.snap
}

package() {
    cd "${srcdir}"

    install -dm755 "${pkgdir}/opt/haruneko"
    cp -a "${srcdir}/snap/." "${pkgdir}/opt/haruneko/"
    rm -rf "${pkgdir}/opt/haruneko/snap" \
           "${pkgdir}/opt/haruneko/meta" \
           "${pkgdir}/opt/haruneko/usr"

    install -Dm755 "${srcdir}/haruneko.sh" "${pkgdir}/usr/bin/haruneko"
    install -Dm644 "${srcdir}/haruneko.desktop" "${pkgdir}/usr/share/applications/haruneko.desktop"
}