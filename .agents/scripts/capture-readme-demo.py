"""Capture actual offline-audit commands in xterm for the README.

Requires Python, xterm, Xvfb and ffmpeg. No network or account data is used.
Set SEO_KIT_DEMO_XTERM to override the xterm executable.
"""

import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time


def main():
    kit = Path(__file__).resolve().parents[2]
    output = kit / "docs/images"
    terminal = os.environ.get("SEO_KIT_DEMO_XTERM") or shutil.which("xterm")
    if not terminal or not all(shutil.which(name) for name in ("Xvfb", "ffmpeg")):
        sys.exit("Capture requires xterm, Xvfb and ffmpeg.")
    with tempfile.TemporaryDirectory(prefix="seo-kit-cli-demo-") as temporary:
        project = Path(temporary)
        (project / "dist/about").mkdir(parents=True)
        (project / "audits").mkdir()
        template = '<!doctype html><html lang="en"><head><title>{title}</title><meta name="description" content="{description}"><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="canonical" href="https://example.org{route}"></head><body><h1>{heading}</h1><a href="{link}">{anchor}</a></body></html>'
        (project / "dist/index.html").write_text(template.format(title="Home | Example", description="A small demonstration website.", route="/", heading="Home", link="/about/", anchor="About this example"))
        (project / "dist/about/index.html").write_text(template.format(title="Home | Example", description="About this demonstration website.", route="/about/", heading="About", link="/missing/", anchor="Visit the home page"))
        (project / "dist/robots.txt").write_text("User-agent: *\nAllow: /\nSitemap: https://example.org/sitemap.xml\n")
        (project / "dist/sitemap.xml").write_text('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.org/</loc></url><url><loc>https://example.org/about/</loc></url></urlset>')
        (project / "show-report.py").write_text('''import json, sys, textwrap
r = json.load(open(sys.argv[1]))
print(f"SEO audit: {r['base_url']} ({r['pages']} pages)")
print(f"Score: {r['score']}/100 | Coverage: {r['coverage']}% | Rubric: {r['scoring_version']}")
print("Status: " + ("complete" if r['complete'] else "provisional"))
for c in r['checks']:
    if c['status'] == 'fail':
        print(f"[FAIL] {c['id']}")
        for f in c['findings']:
            if f['status'] == 'fail': print(f"  {f['location']}: {f['detail']}")
print(textwrap.fill("Unmeasured: " + ", ".join(c['id'] for c in r['checks'] if c['status'] == 'unmeasured'), width=105))
if 'comparison' in r:
    c = r['comparison']
    print(f"Follow-up: new={len(c['new_failures'])}, persistent={len(c['persistent_failures'])}, resolved={len(c['resolved_failures'])}")
    print(f"Comparable score delta: {c['score_delta']}")
print("Checklist score is not a ranking prediction.")
''')
        (project / "fix-demo.py").write_text('''from pathlib import Path
import re
p = Path("dist/about/index.html")
before = p.read_text()
p.write_text(before.replace("Home | Example", "About | Example").replace('href="/missing/"', 'href="/"'))
after = p.read_text()
print("Updated dist/about/index.html")
for label, pattern in [("Title", r"<title>(.*?)</title>"), ("Internal link", r'<a href="(.*?)"')]:
    print(f"{label}: {re.search(pattern, before)[1]} -> {re.search(pattern, after)[1]}")
''')
        env = dict(os.environ, SEO_KIT_DIR=str(kit), DEMO_PYTHON=sys.executable)
        audit = 'audit --site dist --base-url https://example.org'
        phases = [
            ("01-audit", [audit + ' --format json --output audits/before.json', '"$DEMO_PYTHON" show-report.py audits/before.json']),
            ("02-fix", ['"$DEMO_PYTHON" fix-demo.py']),
            ("03-verify", [audit + ' --format json --baseline audits/before.json --output audits/after.json', '"$DEMO_PYTHON" show-report.py audits/after.json']),
        ]
        # Let Xvfb choose an unused display rather than sharing a user display.
        with tempfile.TemporaryFile() as display_file:
            server = subprocess.Popen(["Xvfb", "-displayfd", str(display_file.fileno()), "-screen", "0", "1440x720x24", "-nolisten", "tcp"], pass_fds=(display_file.fileno(),), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                display = ""
                for _ in range(100):
                    display_file.seek(0)
                    display = display_file.read().decode().strip()
                    if display:
                        break
                    time.sleep(0.05)
                if not display:
                    raise RuntimeError("Xvfb did not start")
                env["DISPLAY"] = ":" + display
                output.mkdir(exist_ok=True)
                for name, commands in phases:
                    done = project / (name + ".done")
                    shell = ["set -eu", "export PS1='$ '", 'audit() { "$DEMO_PYTHON" "$SEO_KIT_DIR/.agents/scripts/audit.py" "$@"; }']
                    for command in commands:
                        shown = command.replace('"$DEMO_PYTHON"', "python3")
                        shell += ["printf '%s\\n' " + shlex.quote("$ " + shown), command]
                    shell += ["touch " + shlex.quote(str(done)), "sleep 30"]
                    script = project / (name + ".sh")
                    script.write_text("\n".join(shell) + "\n")
                    process = subprocess.Popen([terminal, "-geometry", "142x34+0+0", "-fa", "DejaVu Sans Mono", "-fs", "12", "-bg", "#101820", "-fg", "#e9f1f7", "-b", "20", "+sb", "-e", "bash", str(script)], cwd=project, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    try:
                        for _ in range(200):
                            if done.exists():
                                break
                            if process.poll() is not None:
                                raise RuntimeError("Terminal command failed: " + name)
                            time.sleep(0.05)
                        if not done.exists():
                            raise RuntimeError("Capture timed out: " + name)
                        time.sleep(0.3)
                        size = "1440x180" if name == "02-fix" else "1440x440"
                        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "x11grab", "-draw_mouse", "0", "-video_size", size, "-i", env["DISPLAY"], "-frames:v", "1", str(output / ("cli-" + name + ".png"))], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                    finally:
                        process.terminate()
                        process.wait()
                before = json.loads((project / "audits/before.json").read_text())
                after = json.loads((project / "audits/after.json").read_text())
                if {item["check"] for item in after["comparison"]["resolved_failures"]} != {"onpage.unique_title", "technical.internal_links"}:
                    raise RuntimeError("Demo did not resolve the two intended failures")
                print(json.dumps({"before_score": before["score"], "after_score": after["score"], "coverage": after["coverage"], "comparison": after["comparison"]}, indent=2))
            finally:
                server.terminate()
                server.wait()


if __name__ == "__main__":
    main()
