#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

# Rebuild every public-site screenshot from the real 320x240 badge UI.
# The emulator profile and capture helper are staged only for this run and are
# restored by the EXIT trap, even when the emulator or image conversion fails.

project_dir="$(cd .. && pwd -P)"
app_id="com.enigmeta.foxhunt"
mpos_dir="${MPOS_DIR:-$HOME/MicroPythonOS}"
internal_dir="$mpos_dir/internal_filesystem"
fixture="$project_dir/tools/server-screenshot-config.json"
helper_src="$project_dir/tools/capture_server_screens.py"
helper_dst="$internal_dir/foxhunt_server_capture.py"
screens_dir="$project_dir/server/static/screens"
work_dir="$(mktemp -d "${TMPDIR:-/tmp}/foxhunt-screens.XXXXXX")"
fifo="$work_dir/emulator-input"
log="$work_dir/emulator.log"
runner_pid=""
emulator_pid=""
files_staged=0

screens=(
    welkom maatje-kop maatje-extra ingeschreven
    boek oppad jacht code gevangen snuffelen vonk plukken oogst
    beest voeren dossier school vliegen vangen dansen vriendenboekje
)

profile_paths=(
    "$internal_dir/data/$app_id.lora/config.json"
    "$internal_dir/prefs/$app_id.lora/config.json"
)

backup_file() {
    local path="$1"
    local key="$2"
    if [[ -f "$path" ]]; then
        cp "$path" "$work_dir/$key.backup"
        : > "$work_dir/$key.existed"
    fi
}

restore_file() {
    local path="$1"
    local key="$2"
    if [[ -f "$work_dir/$key.existed" ]]; then
        mkdir -p "$(dirname "$path")"
        cp "$work_dir/$key.backup" "$path"
    else
        rm -f "$path"
    fi
}

stop_emulator() {
    if [[ -n "$emulator_pid" ]] && kill -0 "$emulator_pid" 2>/dev/null; then
        kill "$emulator_pid" 2>/dev/null || true
        for _ in 1 2 3 4 5; do
            kill -0 "$emulator_pid" 2>/dev/null || break
            sleep 0.2
        done
        if kill -0 "$emulator_pid" 2>/dev/null; then
            kill -9 "$emulator_pid" 2>/dev/null || true
        fi
    fi
    if [[ -n "$runner_pid" ]] && kill -0 "$runner_pid" 2>/dev/null; then
        kill "$runner_pid" 2>/dev/null || true
    fi
}

cleanup() {
    stop_emulator
    if [[ "$files_staged" -eq 1 ]]; then
        restore_file "${profile_paths[0]}" profile-data
        restore_file "${profile_paths[1]}" profile-prefs
        restore_file "$helper_dst" helper
    fi
    rm -rf "$work_dir"
}
trap cleanup EXIT INT TERM

[[ -x "$project_dir/scripts/run_on_mac.sh" ]] || {
    echo "error: missing scripts/run_on_mac.sh" >&2
    exit 1
}
[[ -f "$fixture" && -f "$helper_src" ]] || {
    echo "error: screenshot fixture files are missing" >&2
    exit 1
}
command -v ffmpeg >/dev/null || {
    echo "error: ffmpeg is required to convert RGB565 captures" >&2
    exit 1
}

backup_file "${profile_paths[0]}" profile-data
backup_file "${profile_paths[1]}" profile-prefs
backup_file "$helper_dst" helper
files_staged=1
for path in "${profile_paths[@]}"; do
    mkdir -p "$(dirname "$path")"
    cp "$fixture" "$path"
done
cp "$helper_src" "$helper_dst"
mkdir -p "$work_dir/raw" "$work_dir/png" "$screens_dir"
mkfifo "$fifo"

"$project_dir/scripts/run_on_mac.sh" --lora < "$fifo" > "$log" 2>&1 &
runner_pid="$!"
exec 3> "$fifo"

# Boot includes MicroPythonOS and the app's non-visual router. Wait for Home to
# settle before replacing its activity stack with the capture fixtures.
for _ in $(seq 1 60); do
    if grep -q "apps.py _launch_activity" "$log"; then
        break
    fi
    kill -0 "$runner_pid" 2>/dev/null || {
        echo "error: emulator exited during startup" >&2
        sed -n '1,240p' "$log" >&2
        exit 1
    }
    sleep 0.5
done
sleep 2

emulator_pid="$(pgrep -P "$runner_pid" -f 'lvgl_micropy_macOS|lvgl_micropy_unix' | head -n 1 || true)"
if [[ -z "$emulator_pid" ]]; then
    echo "error: could not identify the emulator process" >&2
    exit 1
fi

printf '%s\n' "import foxhunt_server_capture as cap" >&3
for name in "${screens[@]}"; do
    printf "cap.show('%s')\n" "$name" >&3
    sleep 1
    printf "cap.shot('%s/raw/%s.raw')\n" "$work_dir" "$name" >&3
    sleep 0.25
done
printf '%s\n' "print('CAPTURE_COMPLETE')" >&3

for _ in $(seq 1 180); do
    grep -q "CAPTURE_COMPLETE" "$log" && break
    kill -0 "$emulator_pid" 2>/dev/null || {
        echo "error: emulator exited while capturing screenshots" >&2
        sed -n '1,320p' "$log" >&2
        exit 1
    }
    sleep 0.5
done
if ! grep -q "CAPTURE_COMPLETE" "$log"; then
    echo "error: timed out while capturing screenshots" >&2
    sed -n '1,320p' "$log" >&2
    exit 1
fi

for name in "${screens[@]}"; do
    raw="$work_dir/raw/$name.raw"
    png="$work_dir/png/$name.png"
    [[ "$(wc -c < "$raw")" -eq 153600 ]] || {
        echo "error: incomplete framebuffer for $name" >&2
        exit 1
    }
    ffmpeg -loglevel error -y \
        -f rawvideo -pixel_format rgb565le -video_size 320x240 -i "$raw" \
        -vf "scale=640:480:flags=neighbor" -frames:v 1 "$png"
    if command -v magick >/dev/null; then
        magick "$png" -strip "$screens_dir/$name.png"
    else
        cp "$png" "$screens_dir/$name.png"
    fi
done

if grep -q "activity.onCreate caught exception\|CAPTURE_ERROR" "$log"; then
    echo "error: an activity failed while rendering" >&2
    sed -n '1,360p' "$log" >&2
    exit 1
fi

echo "Updated ${#screens[@]} screenshots in $screens_dir"
