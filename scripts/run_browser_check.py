"""Actual Chromium software E2E against a fresh localhost sandbox, egress blocked."""
import http.client
import importlib.metadata
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
from uuid import uuid4

from playwright.sync_api import sync_playwright, expect

from decisionproof.contracts import utc
from decisionproof.service import provision

ROOT = Path(__file__).resolve().parents[1]


def main():
    evidence = ROOT/"docs/evidence/p1a"
    evidence.mkdir(parents=True,exist_ok=True)
    private = ROOT/".preflight/browser"/str(uuid4())
    password = secrets.token_urlsafe(24)
    provision(private,password)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1",0));port=sock.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    log = (private/"server.log").open("w",encoding="utf-8")
    def start():
        process = subprocess.Popen([sys.executable,"-m","decisionproof","serve","--directory",str(private),"--port",str(port),"--predecessor-stopped"],
            cwd=ROOT,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
        for _ in range(200):
            if process.poll() is not None:
                raise RuntimeError("Local test server exited; inspect private server.log")
            try:
                connection = http.client.HTTPConnection("127.0.0.1",port,timeout=0.5)
                connection.request("GET","/")
                if connection.getresponse().status==200:
                    connection.close();return process
            except OSError:
                pass
            time.sleep(0.1)
        raise TimeoutError("Local server startup")
    def stop(process):
        if process.poll() is None:
            process.terminate();process.wait(timeout=15)
    process = start()
    clicks=[];errors=[];blocked=[]
    started=time.perf_counter()
    try:
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(headless=True)
            context=browser.new_context(viewport={"width":1440,"height":1000},device_scale_factor=1)
            def route(request):
                if request.request.url.startswith(origin+"/"):
                    request.continue_()
                else:
                    blocked.append(request.request.url.split('?')[0]);request.abort()
            context.route("**/*",route)
            page=context.new_page();page.on("pageerror",lambda e:errors.append(str(e)))
            def click(selector):
                page.locator(selector).click();clicks.append(selector)
            def login():
                page.locator('#password').fill(password)
                click('#login-form button[type=submit]')
                expect(page.locator('#workspace')).to_be_visible()
                expect(page.locator('#scenario option')).to_have_count(16)
            def shot(name):
                page.screenshot(path=str(evidence/(name+'.png')),full_page=True,animations="disabled")
            def current_case():
                cases=context.request.get(origin+'/api/cases').json()
                return context.request.get(origin+'/api/cases/'+cases[0]['case_id']).json()
            page.goto(origin);login()
            click('#analyze');expect(page.locator('#decision-status')).to_contain_text('READY FOR HUMAN REVIEW')
            expect(page.locator('#decision-delta')).to_contain_text('B exposed: None → True')
            shot('browser-decision-delta')
            click('[data-screen=evidence]');click('.citation >> nth=0');shot('browser-evidence')
            click('[data-screen=execution]')
            click('#propose-plan');expect(page.locator('#approve-plan')).to_be_visible()
            click('#approve-plan');expect(page.locator('#admit-action')).to_be_visible()
            click('#admit-action');expect(page.locator('#authorize-action')).to_be_visible()
            shot('browser-separate-authorization')
            click('#authorize-action');expect(page.locator('#execute-action')).to_be_visible()
            click('#execute-action');expect(page.locator('#task-receipt')).to_contain_text('Verified sandbox task')
            hero=current_case();assert len(hero['tasks'])==1 and hero['actions'][0]['state']=='Succeeded'
            hero_clicks=len(clicks);shot('browser-execution')
            page.reload();expect(page.locator('#workspace')).to_be_visible()
            click('#case-list button >> nth=0');click('[data-screen=execution]')
            expect(page.locator('#task-receipt')).to_be_visible()
            # Lose only the HTTP acknowledgment after a real successful local dispatch.
            # The UI must read durable state, never issue a second execute POST.
            lost_ack_count=[0]
            def lose_http_ack(route):
                lost_ack_count[0]+=1
                response=route.fetch()
                assert response.status==200
                route.abort()
            context.route('**/api/actions/*/execute',lose_http_ack,times=1)
            page.locator('#scenario').select_option('s01');click('#analyze')
            expect(page.locator('#decision-status')).to_contain_text('READY FOR HUMAN REVIEW')
            click('[data-screen=execution]');click('#propose-plan');click('#approve-plan');click('#admit-action');click('#authorize-action');click('#execute-action')
            expect(page.locator('#task-receipt')).to_contain_text('Verified sandbox task')
            assert len(current_case()['tasks'])==1 and page.locator('#execute-action').count()==0 and lost_ack_count[0]==1
            page.locator('#scenario').select_option('s12');click('#analyze')
            expect(page.locator('#decision-status')).to_contain_text('READY FOR HUMAN REVIEW')
            click('[data-screen=execution]');click('#propose-plan');click('#approve-plan');click('#admit-action');click('#deny-action')
            expect(page.locator('#execution-content')).to_contain_text('Authorization denied')
            assert not current_case()['tasks'];assert page.locator('#execute-action').count()==0
            shot('browser-denied')
            page.locator('#scenario').select_option('s08');click('#analyze')
            expect(page.locator('#decision-status')).to_contain_text('ABSTAIN')
            click('[data-screen=execution]');expect(page.locator('#propose-plan')).to_be_disabled();shot('browser-abstain')
            assert not current_case()['runs']
            stop(process);process=start()
            page.reload();expect(page.locator('#login-dialog')).to_be_visible();login()
            click('#case-list button:has-text("S09 / original")');click('[data-screen=execution]')
            expect(page.locator('#task-receipt')).to_contain_text('Verified sandbox task')
            persisted=context.request.get(origin+'/api/cases/'+hero['case']['case_id']).json()
            assert persisted['tasks']==hero['tasks'] and persisted['history']==hero['history']
            assert not errors,errors
            result={"status":"PASS","utc":utc(),"browser":"Chromium "+browser.version,"playwright":importlib.metadata.version('playwright'),
                "kind":"Actual headless Chromium UI test; scripted authenticated review, not an owner click or live sponsor run",
                "hero_state":hero['actions'][0]['state'],"hero_task_rows":len(hero['tasks']),"hero_retrieval_rounds":hero['history'][-1]['rounds'],
                "hero_rankings":[hero['delta']['previous_ranking'],hero['delta']['current_ranking']],
                "denial_zero_tasks":True,"abstention_zero_runs":True,"new_server_process_history_persisted":True,
                "lost_http_ack_read_only_refresh_one_execute":lost_ack_count[0]==1,
                "hero_control_activations_including_login_navigation":hero_clicks,"total_control_activations":len(clicks),
                "elapsed_seconds":round(time.perf_counter()-started,3),"page_errors":errors,"blocked_external_requests":blocked,
                "screenshot_files":[p.name for p in evidence.glob('browser-*.png')]}
            (evidence/'browser-result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
            print(json.dumps(result,indent=2));browser.close()
    finally:
        stop(process);log.close()


if __name__=='__main__':
    main()
