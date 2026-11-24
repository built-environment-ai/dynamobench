import argparse, json, pathlib
from verifier.summarize import aggregate_reports

def main():
    p = argparse.ArgumentParser(prog='dynamobench', description='DynamoBench v0.1 CLI')
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('list-tasks')
    s = sub.add_parser('summarize')
    s.add_argument('--reports-dir', default='reports')
    s.add_argument('--out-json', default='reports/benchmark_summary.json')
    s.add_argument('--out-md', default='reports/BENCHMARK_LEADERBOARD.md')
    args = p.parse_args()
    if args.cmd == 'list-tasks':
        for sp in sorted(pathlib.Path('benchmark/tasks').glob('*/specification.json')):
            d = json.loads(sp.read_text(encoding='utf-8-sig'))
            print('{0} | {1} | {2}'.format(d['task_id'], d.get('category', 'n/a'), d.get('title', '')))
    elif args.cmd == 'summarize':
        res = aggregate_reports(pathlib.Path(args.reports_dir), pathlib.Path(args.out_json), pathlib.Path(args.out_md))
        print('Runs: {0} | Exec: {1:.1f}% | Semantic: {2:.1f}% | SilentFail: {3:.1f}%'.format(res['total_runs'], res['metrics']['execution_pass_rate']*100, res['metrics']['semantic_pass_rate']*100, res['metrics']['silent_failure_rate']*100))

if __name__ == '__main__':
    main()
