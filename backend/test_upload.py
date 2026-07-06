import requests

with open('test.csv', 'w') as f:
    f.write("url\nhttps://example.com/product")

with open('test.csv', 'rb') as f:
    r = requests.post(
        "http://127.0.0.1:8000/jobs/upload-csv?task_name=task-1&url_column=url&priority=low&product_type=simple&created_by=admin",
        files={"file": f}
    )
print(r.status_code)
print(r.json())
