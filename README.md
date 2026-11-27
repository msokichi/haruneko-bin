# haruneko-bin

Unofficial x86_64 package for the Haruneko project’s HakuNeko Electron client on Arch Linux, CachyOS, EndeavourOS, and compatible distributions. The package repackages upstream’s canary binary and runs independently of Snap. It is maintained separately from upstream and the distributions.

## Install or update

On an up-to-date Arch-based system, install the build prerequisites, clone this repository, and run makepkg as your regular user. Pacman may ask for elevation to install dependencies and the finished package.

```sh
sudo pacman -S --needed base-devel git
git clone https://github.com/msokichi/haruneko-bin.git
cd haruneko-bin
makepkg -si
haruneko
```

For subsequent updates, pull the packaging changes and run `makepkg -si` again. The package version follows the upstream UTC release tag, with the Arch package revision after the hyphen.

Prebuilt packages and an AUR submission are planned. This checkout builds an unsigned local package. Install a package you built with `sudo pacman -U ./haruneko-bin-20260903.1833-1-x86_64.pkg.tar.zst`, or use the installation step built into `makepkg -si`.

To uninstall, run `sudo pacman -Rns haruneko-bin`. Pacman removes the package files. Preferences and downloads in your user directories stay in place.

## Runtime and provenance

- The recipe pins the x86_64 Snap from canary `260903T1833` and verifies its SHA-256 against the GitHub release asset digest. This identifies the published asset bytes. The package bundles Electron 44.1.1 and uses Arch libraries for NSS, GTK and other system dependencies. [Upstream release](https://github.com/manga-download/haruneko/releases/tag/260903T1833)
- Launch **HakuNeko** from your desktop menu or run `haruneko`. Electron selects Wayland in a Wayland session. To try XWayland, run `haruneko --ozone-platform=x11`. The launcher forwards arguments and uses Electron’s default profile location, typically `${XDG_CONFIG_HOME:-$HOME/.config}/hakuneko-electron`.
- Chromium uses the host’s unprivileged user namespaces and the packaged sandbox helper stays at mode `0755`. Upstream disables sandboxing and web security for the main renderer and loads the application interface from `https://app.hakuneko.download`. The package preserves these upstream settings. Canary builds may be unstable. [Upstream Electron source](https://github.com/manga-download/haruneko/blob/f8e87b4ad2e35b2b22f88002a23006cd784e209c/app/electron/src/Main.ts)
- Haruneko and its upstream artwork are distributed with the repository’s Unlicense. The package includes the Electron, Chromium, Commander and ws notices. The exact bundled `websocket-rpc` source revision has no explicit license in its source archive or package manifest. Clarify redistribution rights with upstream before publishing binaries. [Haruneko Unlicense](https://github.com/manga-download/haruneko/blob/f8e87b4ad2e35b2b22f88002a23006cd784e209c/UNLICENSE) · [Bundled websocket-rpc revision](https://github.com/manga-download/websocket-rpc/tree/14d0bfc08601ee8adfe9f8869d9cc7c9f6238700)

## Report issues and contribute

Report installation, launcher, or system dependency problems in the packaging issue tracker. Include the package version, distribution, display backend and relevant terminal output. Report application behavior and connector problems upstream. [Packaging issues](https://github.com/msokichi/haruneko-bin/issues) · [Upstream issues](https://github.com/manga-download/haruneko/issues)

For packaging changes, run `makepkg --verifysource`, `makepkg -s --cleanbuild`, `desktop-file-validate haruneko.desktop` and `namcap PKGBUILD ./*.pkg.tar.zst`. Regenerate `.SRCINFO` with `makepkg --printsrcinfo > .SRCINFO`. For a new upstream tag, verify the asset layout and digest and reset `pkgrel` to 1. For a packaging-only change, increment `pkgrel`.

The package keeps the prebuilt runtime together under `/opt/haruneko` so Electron can resolve its adjacent resources and libraries. Namcap flags the ELF path and the unstripped upstream Vulkan loader. Its `libdl` and `libpthread` findings refer to the upstream binaries’ ELF entries, and its `sh` finding refers to the launcher’s `/bin/sh` interpreter, provided by Bash on Arch.

For a manual runtime check, launch HakuNeko from the desktop menu, change a preference, and restart it to verify that the preference persists. Repeat with `haruneko --ozone-platform=x11` in a Wayland session with XWayland. Check a connector and a download separately from application startup.
