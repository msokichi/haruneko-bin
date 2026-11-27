#!/usr/bin/env bash
set -euo pipefail

update_dir=$1
if [[ ! -f $update_dir/PKGBUILD ]]; then
    exit 0
fi
tag=$(sed -nE 's/^_upstream_tag=([0-9]{6}T[0-9]{4})$/\1/p' "$update_dir/PKGBUILD")
[[ $tag =~ ^[0-9]{6}T[0-9]{4}$ ]]
branch="automation/haruneko-$tag"

existing=$(gh pr list --repo "$GITHUB_REPOSITORY" --base main --head "$branch" \
    --state all --json isCrossRepository --jq 'any(.[]; .isCrossRepository == false)')
if [[ $existing == true ]]; then
    printf 'A pull request already exists for %s.\n' "$tag"
    exit 0
fi

git_authenticated() {
    git -c credential.helper= -c 'credential.helper=!gh auth git-credential' "$@"
}

base=$(git_authenticated ls-remote --exit-code origin refs/heads/main | cut -f1)
if [[ $base != "$(git rev-parse HEAD)" ]]; then
    printf 'The main branch changed during the update. Retry against the new head.\n' >&2
    exit 1
fi

cp "$update_dir/"{PKGBUILD,.SRCINFO} .
git add -- PKGBUILD .SRCINFO
git diff --cached --check
if git diff --cached --quiet; then
    exit 0
fi

remote_branch=$(git_authenticated ls-remote origin "refs/heads/$branch")
if [[ -n $remote_branch ]]; then
    git_authenticated fetch --no-tags origin "refs/heads/$branch"
    if [[ $(git rev-parse 'FETCH_HEAD^') != "$base" ||
        $(git rev-parse 'FETCH_HEAD^{tree}') != "$(git write-tree)" ]]; then
        printf 'Existing branch %s differs from the prepared update.\n' "$branch" >&2
        exit 1
    fi
else
    git -c user.name='github-actions[bot]' \
        -c user.email='41898282+github-actions[bot]@users.noreply.github.com' \
        commit --no-gpg-sign -m "chore: package Haruneko $tag"
    git_authenticated push origin "HEAD:refs/heads/$branch"
fi

gh pr create --repo "$GITHUB_REPOSITORY" --base main --head "$branch" \
    --title "chore: package Haruneko $tag" \
    --body "Package upstream canary [$tag](https://github.com/manga-download/haruneko/releases/tag/$tag). The updater checked the Snap layout and pinned the source checksums. Review the packaging CI results before merging."
