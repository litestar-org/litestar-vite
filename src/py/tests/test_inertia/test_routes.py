from litestar_vite.inertia.routes import EXCLUDED_METHODS, generate_js_routes
from tests.test_app.app import app


def test_route_export() -> None:
    routes = generate_js_routes(app=app)
    test_1 = {"POST", "OPTIONS"}
    test_2 = {"POST", "OPTIONS", "HEAD"}
    test_3 = {"HEAD"}
    test_4 = {"GET"}
    assert len(test_1.difference(EXCLUDED_METHODS)) == 1
    assert len(test_2.difference(EXCLUDED_METHODS)) == 1
    assert len(test_3.difference(EXCLUDED_METHODS)) == 0
    assert test_4.isdisjoint(EXCLUDED_METHODS)
    routes = generate_js_routes(app=app)
    json_response = routes.formatted_routes
    assert json_response
    assert routes is not None
