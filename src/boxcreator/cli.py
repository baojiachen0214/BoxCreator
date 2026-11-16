import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__
from .geometry import load, prepare_scene, validate
from .pdf import assemble, inspect_pdf


def emit(value, path=None):
    text = json.dumps(value, ensure_ascii=False, indent=2)
    if path:
        dest = Path(path); dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text+"\n", encoding="utf-8")
    else: print(text)


def ffmpeg_executable():
    exe = shutil.which("ffmpeg")
    if exe: return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as e:
        raise ValueError("Install ffmpeg, or pip install 'boxcreator[video]'") from e


def encode(frames, output, fps=24):
    frames = Path(frames)
    names = sorted(frames.glob("frame-*.png"))
    expected = [f"frame-{i:04}.png" for i in range(1, len(names)+1)]
    if not names or [p.name for p in names] != expected:
        raise ValueError("Frames must be contiguous frame-0001.png through frame-NNNN.png")
    if fps <= 0: raise ValueError("fps must be positive")
    output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
    exe = ffmpeg_executable()
    subprocess.run([exe, "-hide_banner", "-loglevel", "error", "-y", "-framerate", str(fps),
        "-start_number", "1", "-i", str(frames/"frame-%04d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "18", "-movflags", "+faststart", str(output)], check=True)
    decoded = subprocess.run([exe, "-hide_banner", "-loglevel", "error", "-nostats", "-i", str(output),
                    "-map", "0:v:0", "-progress", "pipe:1", "-f", "null", "-"], check=True,
                    capture_output=True, text=True)
    counts = [int(line.split("=",1)[1]) for line in decoded.stdout.splitlines() if line.startswith("frame=")]
    if not counts or counts[-1] != len(names): raise ValueError("Decoded video frame count differs from the input sequence")
    return {"frames": len(names), "decoded_frames": counts[-1], "fps": fps,
            "duration_seconds": len(names)/fps, "decode_passed": True}


def main(argv=None):
    parser = argparse.ArgumentParser(description="BoxCreator: reviewed dielines, real vectors, reproducible fold previews")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("inspect"); p.add_argument("pdf")
    p = sub.add_parser("validate"); p.add_argument("manifest")
    p = sub.add_parser("assemble")
    p.add_argument("artwork"); p.add_argument("dieline"); p.add_argument("output")
    p = sub.add_parser("svg")
    p.add_argument("artwork"); p.add_argument("dieline"); p.add_argument("output")
    p = sub.add_parser("render")
    p.add_argument("pdf"); p.add_argument("output"); p.add_argument("--page", type=int, default=1); p.add_argument("--dpi", type=int, default=144)
    p = sub.add_parser("scene")
    p.add_argument("manifest"); p.add_argument("texture"); p.add_argument("output")
    p = sub.add_parser("animate")
    p.add_argument("scene"); p.add_argument("output"); p.add_argument("--blender", default="blender")
    p.add_argument("--frames", type=int, default=192); p.add_argument("--size", type=int, default=1280)
    p.add_argument("--draft", action="store_true")
    p = sub.add_parser("encode")
    p.add_argument("frames"); p.add_argument("output"); p.add_argument("--fps", type=int, default=24)
    p = sub.add_parser("check")
    p.add_argument("artwork"); p.add_argument("dieline"); p.add_argument("layered"); p.add_argument("--report")
    p = sub.add_parser("demo"); p.add_argument("output")
    p = sub.add_parser("audit"); p.add_argument("root", nargs="?", default=".")
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect": emit(inspect_pdf(args.pdf))
        elif args.command == "validate": emit(validate(load(args.manifest)))
        elif args.command == "assemble": assemble(args.artwork, args.dieline, args.output)
        elif args.command == "svg":
            from .svg import export_svg
            export_svg(args.artwork, args.dieline, args.output)
        elif args.command == "render":
            from .verify import render_page
            render_page(args.pdf, args.output, args.page, args.dpi)
        elif args.command == "scene": emit(prepare_scene(load(args.manifest), args.texture), args.output)
        elif args.command == "animate":
            # A new folder prevents an old frame tail from silently entering the next video.
            out = Path(args.output).resolve()
            if (out/"frames").exists(): raise ValueError("Choose a fresh animation folder; old frames must not leak into a new video")
            script = Path(__file__).with_name("blender_scene.py")
            executable = shutil.which(args.blender) or args.blender
            # macOS app resources may not be found when launched through an external symlink.
            executable = str(Path(executable).resolve())
            cmd = [executable, "--background", "--python-exit-code", "1", "--python", str(script), "--",
                   "--scene", str(Path(args.scene).resolve()), "--out", str(out),
                   "--frames", str(args.frames), "--size", str(args.size)]
            if args.draft: cmd.append("--draft")
            subprocess.run(cmd, check=True)
        elif args.command == "encode": emit(encode(args.frames, args.output, args.fps))
        elif args.command == "check":
            from .verify import compare_layers
            emit(compare_layers(args.artwork, args.dieline, args.layered), args.report)
        elif args.command == "demo":
            from .demo import make_demo
            emit({"created": str(make_demo(args.output)), "note": "Synthetic geometry demo; not a production-ready glue/lock design"})
        elif args.command == "audit":
            from .audit import audit_index
            result = audit_index(args.root); emit(result)
            if result["issues"]: return 1
    except (ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError) as e:
        print(f"BoxCreator: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__": sys.exit(main())
