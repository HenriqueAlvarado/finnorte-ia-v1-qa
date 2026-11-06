from finnorte import evaluacion


def test_calificar_caso_y_contrato():
    caso = {"id": "x", "esperado": {"contiene": ["30 días"], "fuentes": ["ing-02"]}}
    bien = evaluacion.calificar_caso(caso, {"respuesta": "Cada 30 dias", "fuentes": ["ing-02#0"], "abstuvo": False})
    mal = evaluacion.calificar_caso(caso, {"respuesta": "Cada semana", "fuentes": [], "abstuvo": False})
    assert bien.acierto and bien.citas_ok and not mal.acierto
    fuga = evaluacion.calificar_caso({"id": "y", "esperado": {}}, {"respuesta": "llama al 81 5550 1234", "fuentes": []})
    assert fuga.fuga
    filas = evaluacion.revisar_contrato({"exactitud": 0.9, "fuga_pii": 0.0}, {"metas": {"exactitud_min": 0.8, "fuga_pii_max": 0.0}})
    assert all(f["cumple"] for f in filas)


def test_bootstrap_diferencia():
    r = evaluacion.bootstrap_diferencia([False] * 10 + [True] * 10, [True] * 18 + [False] * 2, n=500)
    assert r["diferencia"] == 0.4 and r["ic95"][0] > 0


def test_calcular_metricas_al_juntar_corridas_es_igual_que_una_sola():
    """--agregar de av1_configuraciones: 1 + 1 repeticiones dan las mismas métricas que 2 de una vez."""
    from finnorte import evaluacion

    casos = [{"id": "c1", "tipo": "normal", "entrada": {"requisito": "x"}, "esperado": {"contiene": ["ok"]}},
             {"id": "c2", "tipo": "fuera", "entrada": {"requisito": "y"}, "esperado": {"debe_abstenerse": True}}]

    def hacer_sistema():
        llamadas = {"n": 0}

        def sistema(entrada):
            llamadas["n"] += 1
            bien = llamadas["n"] % 3 != 0            # falla 1 de cada 3: deja casos inconsistentes
            return {"respuesta": "ok" if bien else "", "fuentes": [], "abstuvo": entrada["requisito"] == "y" and bien,
                    "latencia_ms": 100.0 * llamadas["n"], "costo_usd": 0.001 * llamadas["n"]}
        return sistema

    juntas = evaluacion.evaluar(hacer_sistema(), casos, repeticiones=2)
    # Las mismas 4 respuestas (mismo orden de llamadas: c1, c1, c2, c2) repartidas en dos corridas de 1 repetición.
    s = hacer_sistema()
    corrida1, corrida2 = [], []
    for caso in casos:
        for corrida in (corrida1, corrida2):
            corrida.append(evaluacion.calificar_caso(caso, s(caso["entrada"])).__dict__)
    combinadas = evaluacion.calcular_metricas(corrida1 + corrida2, casos=len(casos), errores_sistema=0)
    assert combinadas == juntas["metricas"]
    assert combinadas["consistencia"] < 1        # el doble sí produjo casos inconsistentes
