#!/usr/bin/env bash
set -Eeuo pipefail

umask 022

source_dir="${GITHUB_WORKSPACE:-$(pwd)}"
project="${SPEAKEASY_PROJECT_PATH:-/opt/speakeasy/current}"
service_name="${SPEAKEASY_SERVICE_NAME:-speakeasy-local.service}"
public_base_url="${SPEAKEASY_PUBLIC_BASE_URL:-https://www.newabby.com}"
staging_root="${HOME}/speakeasy-staging/deploy"
backup_root="${HOME}/speakeasy-staging/code-backups"

case "$project" in
  /*) ;;
  *) echo "Project path must be absolute: $project" >&2; exit 2 ;;
esac
if [[ ! "$service_name" =~ ^[A-Za-z0-9_.@-]+$ ]]; then
  echo "Invalid systemd service name: $service_name" >&2
  exit 2
fi
if [[ "$public_base_url" != https://* ]]; then
  echo "Public base URL must use HTTPS." >&2
  exit 2
fi

for command_name in rsync tar curl systemctl journalctl; do
  command -v "$command_name" >/dev/null
done

test -f "$source_dir/app/main.py"
test -f "$source_dir/requirements.txt"
test -d "$project"
test -d "$project/.venv"
test -f "$project/.env"
test -d "$project/uploads"

source_dir=$(cd "$source_dir" && pwd -P)
project=$(cd "$project" && pwd -P)
if [ "$source_dir" = "$project" ]; then
  echo "Runner checkout and production directory must be different." >&2
  exit 2
fi

commit="${GITHUB_SHA:-}"
if [ -z "$commit" ] && [ -f "$source_dir/.release-commit" ]; then
  commit=$(tr -d '\r\n' < "$source_dir/.release-commit")
fi
if [ -z "$commit" ] && [ -d "$source_dir/.git" ]; then
  command -v git >/dev/null
  commit=$(git -C "$source_dir" rev-parse HEAD)
fi
if [[ ! "$commit" =~ ^[0-9a-f]{40}$ ]]; then
  echo "Unable to resolve the 40-character release commit." >&2
  exit 2
fi
if [ -f "$source_dir/.release-commit" ]; then
  if [ "$(tr -d '\r\n' < "$source_dir/.release-commit")" != "$commit" ]; then
    echo "Runner snapshot does not match the requested release commit." >&2
    exit 2
  fi
elif [ -d "$source_dir/.git" ]; then
  command -v git >/dev/null
  if [ "$(git -C "$source_dir" rev-parse HEAD)" != "$commit" ]; then
    echo "Runner checkout does not match the requested release commit." >&2
    exit 2
  fi
else
  echo "Release source has neither a verified snapshot nor a Git checkout." >&2
  exit 2
fi

mkdir -p "$staging_root" "$backup_root"
release_dir=$(mktemp -d "$staging_root/${commit:0:12}.XXXXXX")
backup_dir="$backup_root/$(date +%Y%m%d-%H%M%S)-${commit:0:12}"
mkdir -p "$backup_dir"

cleanup() {
  case "$release_dir" in
    "$staging_root"/*) rm -rf -- "$release_dir" ;;
  esac
}
trap cleanup EXIT

echo "==> Preparing release $commit"
if [ -d "$source_dir/.git" ]; then
  git -C "$source_dir" archive "$commit" | tar -x -C "$release_dir"
else
  rsync -a \
    --exclude=.release-commit \
    "$source_dir/" "$release_dir/"
fi
test -f "$release_dir/PROJECT_STATUS.md"
test -f "$release_dir/scripts/deploy-production-linux.sh"

echo "==> Backing up current application code"
tar \
  --exclude=.env \
  --exclude=.venv \
  --exclude=uploads \
  -czf "$backup_dir/code-before.tar.gz" \
  -C "$project" .

echo "==> Synchronizing release into $project"
rsync -a --delete \
  --exclude=.env \
  --exclude=.venv \
  --exclude=uploads \
  "$release_dir/" "$project/"
printf '%s\n' "$commit" > "$project/.deployment-commit"

echo "==> Installing Python dependencies and compiling"
"$project/.venv/bin/python" -m pip install \
  --disable-pip-version-check \
  -q \
  -r "$project/requirements.txt"
"$project/.venv/bin/python" -m compileall -q "$project/app"

old_pid=$(systemctl show "$service_name" -p MainPID --value)
if [[ ! "$old_pid" =~ ^[1-9][0-9]*$ ]] || [ ! -r "/proc/$old_pid/cmdline" ]; then
  echo "Unable to identify the current service process." >&2
  exit 1
fi
old_command=$(tr '\0' ' ' < "/proc/$old_pid/cmdline")
case "$old_command" in
  *"uvicorn app.main:app"*"--port 8011"*) ;;
  *) echo "Refusing to stop unexpected service process: $old_command" >&2; exit 1 ;;
esac

echo "==> Restarting $service_name"
kill -TERM "$old_pid"

new_pid=""
for _ in $(seq 1 60); do
  candidate_pid=$(systemctl show "$service_name" -p MainPID --value)
  state=$(systemctl is-active "$service_name" 2>/dev/null || true)
  if [ "$state" = "active" ] &&
     [[ "$candidate_pid" =~ ^[1-9][0-9]*$ ]] &&
     [ "$candidate_pid" != "$old_pid" ] &&
     curl -fsS -o /dev/null http://127.0.0.1:8011/login; then
    new_pid="$candidate_pid"
    break
  fi
  sleep 1
done

if [ -z "$new_pid" ]; then
  journalctl -u "$service_name" -n 80 --no-pager
  echo "The local production service did not become healthy." >&2
  exit 1
fi

public_status=""
for _ in $(seq 1 30); do
  public_status=$(curl -L -sS -o /dev/null -w '%{http_code}' \
    --max-time 20 "$public_base_url/login" || true)
  if [ "$public_status" = "200" ]; then
    break
  fi
  sleep 2
done
if [ "$public_status" != "200" ]; then
  echo "Public proxy health check failed with HTTP $public_status." >&2
  exit 1
fi

printf 'status=active\nold_pid=%s\nnew_pid=%s\nbackup=%s\ncommit=%s\npublic_status=%s\n' \
  "$old_pid" \
  "$new_pid" \
  "$backup_dir/code-before.tar.gz" \
  "$commit" \
  "$public_status"

if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  {
    echo "### SpeakEasy production deployment"
    echo
    echo "- Commit: \`$commit\`"
    echo "- Target: \`192.168.1.186:8011\`"
    echo "- Service: \`$service_name\`"
    echo "- Public check: \`$public_status\`"
    echo "- Backup: \`$backup_dir/code-before.tar.gz\`"
  } >> "$GITHUB_STEP_SUMMARY"
fi
