# Skybound Obby

A colorful obstacle-course game with two ways to play:

- **Browser:** the static, browser-native game in [`web/`](./web/), ready for
  GitHub Pages. It uses HTML, CSS, JavaScript modules, Canvas, and the Web Audio
  API; it has no package manager, external runtime dependencies, or downloaded
  art and sound assets.
- **Desktop:** the original Tkinter game in [`obby.py`](./obby.py). It uses
  Python's standard library only.

## Play in a browser

Open [`web/index.html`](./web/index.html) in a modern browser. For local testing,
serve the repository over HTTP from its root (for example, run
`python -m http.server 8000` and visit `http://localhost:8000/web/`). This uses
only Python's standard library; serving over HTTP is recommended for JavaScript
modules.

### Controls

| Input | Action |
| --- | --- |
| `W` / `↑` | Move forward |
| `S` / `↓` | Move backward |
| `A` / `←` | Move left |
| `D` / `→` | Move right |
| `Space` | Jump |
| `Esc` | Pause or resume |
| Touch controls | Move and jump on phones and tablets |

Collect stars to unlock additional avatars. Reach glowing checkpoints as you
climb; red hazards cost a heart. Sound is generated locally in the browser and
starts after the player begins a run, in keeping with browser autoplay rules.

## Publish with GitHub Pages

The workflow at
[`.github/workflows/pages.yml`](./.github/workflows/pages.yml) deploys only
the static `web/` directory—no Python runtime, package install, or build step is
needed.

1. Push the repository to GitHub. The workflow runs on pushes to `main` and can
   also be started manually from the **Actions** tab.
2. In the repository, open **Settings → Pages** and set the build and
   deployment source to **GitHub Actions**.
3. After the workflow succeeds, open the published URL shown in the workflow's
   `github-pages` deployment environment.

If the repository's default branch is not named `main`, update the branch
filter in the workflow to match it.

## Run the desktop game

Run `python obby.py` with Python and Tkinter available. No third-party Python
packages are required. On Windows, sound effects are played asynchronously so
they do not pause the game loop; other platforms use Tkinter's built-in bell.
