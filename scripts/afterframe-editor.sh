
#!/usr/bin/env bash
set -Eeuo pipefail

# AFTERFRAME EDITOR
# Combines generated scenes into one vertical 59-second film.

TARGET_DURATION=59
WIDTH=720
HEIGHT=1280
FPS=30

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ERROR: FFmpeg is not installed."
  exit 1
fi

if ! command -v ffprobe >/dev/null 2>&1; then
  echo "ERROR: FFprobe is not installed."
  exit 1
fi

if [ "$#" -lt 1 ]; then
  echo "Usage: bash scripts/afterframe-editor.sh scene1.mp4 scene2.mp4 ..."
  exit 1
fi

WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT

TOTAL_DURATION=0
INDEX=0
INPUTS=("$@")

echo "AFTERFRAME EDITOR started."
echo "Scenes received: ${#INPUTS[@]}"

for INPUT in "${INPUTS[@]}"; do
  if [ ! -f "$INPUT" ]; then
    echo "ERROR: File not found: $INPUT"
    exit 1
  fi

  DURATION=$(ffprobe -v error \
    -show_entries format=duration \
    -of default=noprint_wrappers=1:nokey=1 "$INPUT")

  if ! awk -v d="$DURATION" 'BEGIN { exit !(d > 0) }'; then
    echo "ERROR: Invalid video: $INPUT"
    exit 1
  fi

  TOTAL_DURATION=$(awk -v a="$TOTAL_DURATION" -v b="$DURATION" \
    'BEGIN { printf "%.3f", a+b }')

  OUTPUT=$(printf "%s/scene_%03d.mp4" "$WORKDIR" "$INDEX")

  echo "Processing scene $((INDEX + 1))..."

  ffmpeg -hide_banner -loglevel error -y \
    -i "$INPUT" \
    -map 0:v:0 \
    -an \
    -vf "scale=${WIDTH}:${HEIGHT}:force_original_aspect_ratio=increase,crop=${WIDTH}:${HEIGHT},setsar=1,fps=${FPS},format=yuv420p" \
    -c:v libx264 \
    -preset veryfast \
    -crf 23 \
    -movflags +faststart \
    "$OUTPUT"

  INDEX=$((INDEX + 1))
done

echo "Total source duration: ${TOTAL_DURATION}s"

if ! awk -v d="$TOTAL_DURATION" -v t="$TARGET_DURATION" \
  'BEGIN { exit !(d >= t) }'; then
  echo "ERROR: Source videos are shorter than 59 seconds."
  echo "More animation scenes are required."
  exit 1
fi

CONCAT_FILE="$WORKDIR/concat.txt"
: > "$CONCAT_FILE"

for ((i=0; i<INDEX; i++)); do
  printf "file '%s/scene_%03d.mp4'\n" "$WORKDIR" "$i" >> "$CONCAT_FILE"
done

echo "Joining scenes..."

ffmpeg -hide_banner -loglevel error -y \
  -f concat -safe 0 \
  -i "$CONCAT_FILE" \
  -t "$TARGET_DURATION" \
  -an \
  -c:v libx264 \
  -preset veryfast \
  -crf 23 \
  -pix_fmt yuv420p \
  -r "$FPS" \
  -movflags +faststart \
  afterframe-final.mp4

FINAL_DURATION=$(ffprobe -v error \
  -show_entries format=duration \
  -of default=noprint_wrappers=1:nokey=1 afterframe-final.mp4)

echo "--------------------------------"
echo "AFTERFRAME EDITOR completed!"
echo "Final video: afterframe-final.mp4"
echo "Duration: ${FINAL_DURATION}s"
echo "Resolution: ${WIDTH}x${HEIGHT}"
echo "--------------------------------"
