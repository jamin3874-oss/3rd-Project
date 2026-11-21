"""Entry point: python main.py"""
import argparse
import json
import os
from pathlib import Path
from config import load_backend_env
from storage import Storage
from agent import Agent, HELP

def run():
    load_backend_env()
    parser=argparse.ArgumentParser(description='SpendWise AI 가계부 에이전트')
    parser.add_argument('--db',default=str(Path(__file__).resolve().parent/'spendwise.db'))
    parser.add_argument('--command',help='한 가지 명령만 실행')
    opts=parser.parse_args()
    agent=Agent(Storage(opts.db))
    print('SpendWise Agent | 데모 CSV는 가상 데이터입니다. 실제 계좌정보를 입력하지 마세요.')
    if opts.command:
        print(json.dumps(agent.execute(opts.command),ensure_ascii=False,indent=2))
        return
    print(HELP)
    while True:
        try: command=input('가계부> ').strip()
        except (EOFError,KeyboardInterrupt): print();break
        if command in ('종료','quit','exit'): break
        print(json.dumps(agent.execute(command),ensure_ascii=False,indent=2))
if __name__=='__main__':run()
