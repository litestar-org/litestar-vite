from litestar_vite.codegen._refs import extract_schema_ref_name, resolve_component_schema_name


def test_extract_schema_ref_name_components_schemas_prefix() -> None:
    assert extract_schema_ref_name("#/components/schemas/User") == "User"
    assert extract_schema_ref_name("#/components/parameters/Foo") is None


def test_resolve_component_schema_name_mangled_prefix_stripping() -> None:
    schemas = {"Granularity": {"enum": ["day", "week"]}}
    assert resolve_component_schema_name("app_domain_insight_schemas__base_Granularity", schemas) == "Granularity"
    assert resolve_component_schema_name("Granularity", schemas) == "Granularity"
    assert resolve_component_schema_name("Unknown", schemas) is None
