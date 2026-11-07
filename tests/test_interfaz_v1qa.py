"""Interfaz v1-qa: la página carga, ofrece los requisitos de ejemplo y corre el flujo sin red (fake/hash)."""
from pathlib import Path

import pytest

st_testing = pytest.importorskip("streamlit.testing.v1")

APP = str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py")


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("EMB_PROVIDER", "hash")
    return st_testing.AppTest.from_file(APP, default_timeout=60)


def test_la_pagina_v1qa_es_la_primera_y_carga(app):
    app.run()
    assert not app.exception
    assert app.sidebar.radio[0].value == "Requisito → pytest (v1-qa)"
    assert "Requisito → pruebas (v1-qa)" in app.title[0].value


def test_ofrece_los_requisitos_de_ejemplo(app):
    app.run()
    opciones = app.selectbox[0].options
    assert "(escribir uno)" in opciones
    assert any(o.startswith("RF12") for o in opciones)


def test_elegir_un_ejemplo_llena_el_requisito_y_corre_el_flujo(app):
    app.run()
    rf12 = next(o for o in app.selectbox[0].options if o.startswith("RF12"))
    app.selectbox[0].select(rf12).run()
    assert "RF12" in app.text_area[0].value
    app.button[0].click().run()
    assert not app.exception
    # Con el proveedor fake el flujo no produce casos reales: lo que importa es que la página
    # muestre el estado de cada etapa y diga dónde se detuvo, sin romperse.
    assert len(app.metric) == 4
    assert app.warning or app.success
