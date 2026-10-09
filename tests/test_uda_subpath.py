"""UDA and LAN routing smoke test."""
from app import app

def test_prefix_and_lan():
    client=app.test_client()
    local=client.get("/")
    assert local.status_code==200
    assert '<base href="/">' in local.get_data(as_text=True)
    headers={"X-Forwarded-Prefix":"/apps/screen-design","X-Forwarded-Host":"tanyaanne.ddns.net","X-Forwarded-Proto":"https"}
    response=client.get("/",headers=headers)
    assert response.status_code==200
    html=response.get_data(as_text=True)
    assert '<base href="/apps/screen-design/">' in html
    assert '/apps/screen-design/static/js/renderer.js' in html
