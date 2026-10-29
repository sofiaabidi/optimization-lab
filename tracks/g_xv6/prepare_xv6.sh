#!/usr/bin/env bash
set -eu

if [ "$#" -ne 2 ] || { [ "$1" != "baseline" ] && [ "$1" != "optimized" ]; }; then
  echo "usage: $0 baseline|optimized NEW_CHECKOUT_DIRECTORY" >&2
  exit 2
fi

mode=$1
target=$2
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
upstream_sha=e93dabeb98431235c6e1a101cb96c73c923fdbc4

if [ -e "$target" ]; then
  echo "target already exists: $target" >&2
  exit 2
fi

git clone https://github.com/mit-pdos/xv6-riscv.git "$target"
git -C "$target" checkout --detach "$upstream_sha"
git -C "$target" apply "$script_dir/patches/0001-benchmark-harness.patch"
if [ "$mode" = "optimized" ]; then
  git -C "$target" apply "$script_dir/patches/0002-priority-accounting.patch"
fi
git -C "$target" diff --check
make -C "$target" -j2 kernel/kernel fs.img

echo "prepared $mode checkout at $target"
