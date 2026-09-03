def test_required_admin_pages_render(client, auth):
    auth.login()
    routes = (
        "/admin",
        "/admin/categories",
        "/admin/appearance/theme",
        "/admin/appearance/branding",
    )
    for route in routes:
        response = client.get(route)
        assert response.status_code == 200, route
