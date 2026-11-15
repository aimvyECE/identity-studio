import argparse
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from .core import read_job, write_new_json

def main():
    parser = argparse.ArgumentParser(description='Local-first fashion identity studio (prototype)')
    sub = parser.add_subparsers(dest='command', required=True)
    serve = sub.add_parser('serve', help='Serve only web assets on loopback, never the photo folder')
    serve.add_argument('--port', type=int, default=8765)
    prepare = sub.add_parser('prepare')
    prepare.add_argument('job'); prepare.add_argument('--output', required=True)
    generate = sub.add_parser('generate', help='Optional local Qwen runner; requires separately installed GPU dependencies and model')
    generate.add_argument('job'); generate.add_argument('--image', required=True)
    generate.add_argument('--output', required=True)
    generate.add_argument('--model-dir', required=True, help='Existing local snapshot, no automatic downloads')
    doctor = sub.add_parser('doctor', help='Read-only local prerequisites report, no downloads')
    doctor.add_argument('--model-dir', help='Optionally inspect a local model configuration, not its weights')
    doctor.add_argument('--probe-cuda', action='store_true', help='Opt in to importing installed PyTorch in a timed subprocess')
    args = parser.parse_args()
    if args.command == 'serve':
        web = Path(__file__).resolve().parent.parent / 'web'
        if not (web / 'index.html').is_file():
            parser.error('web/index.html missing; run from the complete source checkout')
        class Handler(SimpleHTTPRequestHandler):
            def end_headers(self):
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.send_header('Referrer-Policy', 'no-referrer')
                super().end_headers()
            def log_message(self, format, *values):
                pass
        print(f'Open http://127.0.0.1:{args.port}; Ctrl+C to stop. Photos stay in the browser.')
        ThreadingHTTPServer(('127.0.0.1', args.port), partial(Handler, directory=str(web))).serve_forever()
    elif args.command == 'doctor':
        from .doctor import diagnose
        print(json.dumps(diagnose(args.model_dir, args.probe_cuda), indent=2))
    elif args.command == 'prepare':
        job = read_job(args.job)
        write_new_json(args.output, job.manifest())
        print(job.prompt())
    else:
        from .qwen import generate_local
        generate_local(read_job(args.job), args.image, args.output, args.model_dir)

if __name__ == '__main__':
    main()
