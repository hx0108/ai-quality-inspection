import sqlite3, sys, os, json
sys.stdout.reconfigure(encoding='utf-8')

HOST = 'http://localhost:8000'

# Login
import urllib.request
login_data = json.dumps({'account': 'admin', 'password': 'admin123'}).encode()
req = urllib.request.Request(HOST + '/api/v1/auth/login', data=login_data, headers={'Content-Type': 'application/json'})
resp = urllib.request.urlopen(req)
token = json.loads(resp.read())['access_token']
print('Login OK')

# Get module detail
task_id = 'Q-20260318-c2c1edef'
module = '安全管理'
url = HOST + '/api/v1/scoring/module-detail/' + task_id + '/' + module
req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + token})
resp = urllib.request.urlopen(req)
data = json.loads(resp.read())

items_with_issues = [i for i in data.get('items', []) if i.get('issues')]
print('Items with issues: ' + str(len(items_with_issues)))

for item in items_with_issues[:3]:
    print('\n  item: ' + item['item_id'])
    for iss in item['issues']:
        desc = iss.get('description', '')[:40]
        photos = iss.get('photos', [])
        print('    issue: ' + desc + ' photos=' + str(len(photos)))
        for ph in photos:
            # Print all keys to see what fields the API returns
            print('      photo keys: ' + str(list(ph.keys())))
            print('      photo data: ' + str(ph)[:200])

# Test photo file access using the URL from API
if items_with_issues:
    first_issue = items_with_issues[0]['issues'][0]
    photos = first_issue.get('photos', [])
    if photos:
        photo_url = photos[0].get('url') or photos[0].get('file_path') or photos[0].get('photo_url')
        if photo_url:
            full_url = HOST + '/api/v1/' + photo_url if not photo_url.startswith('http') else photo_url
            print('\n=== Testing photo URL ===')
            print('URL: ' + full_url)
            try:
                req = urllib.request.Request(full_url, headers={'Authorization': 'Bearer ' + token})
                resp = urllib.request.urlopen(req)
                print('Status: ' + str(resp.status))
                print('Content-Type: ' + resp.headers.get('Content-Type', ''))
            except Exception as e:
                print('Error: ' + str(e))
