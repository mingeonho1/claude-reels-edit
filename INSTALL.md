# INSTALL.md — instructions for Claude

You are installing the `reels-talk-edit` and `reels-qa` skills from this repository. Work through the steps,
report what you did, and ask before overwriting anything.

1. **Check prerequisites** and report versions: `python3 --version` (3.10+), `ffmpeg -version` (≥ 4.4, must list
   `--enable-libx265`), free disk (≥ 2 GB). If ffmpeg is missing, suggest `brew install ffmpeg` (macOS) or the
   distro package; do not install system packages without asking.
2. **Python packages**: `pip install -r requirements.txt` (add `--break-system-packages` only on externally managed
   Pythons, and say so).
3. **Assets and models**: `bash skills/reels-talk-edit/scripts/fetch_assets.sh`. Models go to `$REELS_MODELS`
   (default `~/reels_models`, ~1.4 GB). On a slow link, offer `--no-models` and run the model step later.
4. **Guest character**: ask the user for a transparent GIF of their guest/character and copy it to
   `skills/reels-talk-edit/assets/character.gif`. If they have none, tell them to set `"modules": {"character": false}`
   in their plans.
5. **Install the skills**:
   - Claude Code: copy (or, if the user wants live edits, symlink) `skills/reels-talk-edit` and `skills/reels-qa`
     into `~/.claude/skills/`. If a skill with the same name exists, show the diff and ask.
   - Codex: copy both folders into `~/.agents/skills/` (same SKILL.md format).
   - Optional: `skills/finance-reels-guard` (finance/investing reel reviewer) — ask whether they make such reels.
   - Claude app / Cowork: zip each skill folder and tell the user to add it under Settings → Skills, or propose them
     as skills if that tool is available.
6. **Adapt paths**: `SKILL.md` uses the author's layout (`~/capcut/me/<NN_topic>/소스/`, Cowork device bridge).
   Ask the user where their footage lives and whether STT and rendering run on the same machine; note the answer
   in a short `LOCAL.md` next to the skill instead of editing SKILL.md.
7. **Smoke test**: `python3 skills/reels-talk-edit/scripts/build_edl.py --help` and
   `python3 skills/reels-talk-edit/scripts/render.py --help` run without import errors; `ls $REELS_MODELS`.

Finish with a 3-line summary: what was installed, where the models are, and the first prompt to try, e.g.
"10번 릴스 편집해줘 — 보정본은 소스/1차_보정.mov".
