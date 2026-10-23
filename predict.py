"""Command-line static analysis; does not execute samples."""
import argparse,json
from pathlib import Path
from dotenv import load_dotenv
from scanner import analyze, MAX_FILE
if __name__=='__main__':
    load_dotenv(Path(__file__).with_name('.env'))
    parser=argparse.ArgumentParser();parser.add_argument('arquivo');args=parser.parse_args()
    try:
        with open(args.arquivo,'rb') as stream:data=stream.read(MAX_FILE+1)
        print(json.dumps(analyze(data,Path(args.arquivo).name),ensure_ascii=False,indent=2))
    except (ValueError,OSError) as e:parser.exit(1,str(e)+'\n')
