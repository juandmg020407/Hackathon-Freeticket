"""La normalizacion de llaves decide que se cruza. Cada caso viene del brief."""

from ft.normalize import (
    clave_nombre,
    fix_dominio,
    local_core,
    norm_email,
    norm_phone,
    sim_nombre,
    transposiciones,
)


class TestEmail:
    def test_mayusculas_y_espacios(self):
        assert norm_email("  ANA.RUIZ@Gmail.COM ")[0] == "ana.ruiz@gmail.com"

    def test_quita_alias(self):
        assert norm_email("ana.ruiz+shows@gmail.com")[0] == "ana.ruiz@gmail.com"

    def test_corrige_dominios_rotos(self):
        for roto in ("gmial.com", "hotmial.com", "outlok.com"):
            assert fix_dominio(roto) in ("gmail.com", "hotmail.com", "outlook.com")

    def test_dominio_desconocido_se_respeta(self):
        assert fix_dominio("empresa-rara.co") == "empresa-rara.co"

    def test_core_ignora_puntos_y_digitos_de_cola(self):
        assert local_core("maria.rodriguez64") == local_core("mariarodriguez")


class TestTelefono:
    def test_cinco_formatos_dan_lo_mismo(self):
        variantes = ["305 254 9013", "+57 305 2549013", "(+57) 305-254-9013",
                     "573052549013", "3052549013"]
        assert len({norm_phone(v) for v in variantes}) == 1

    def test_vacio_no_inventa(self):
        assert norm_phone(None) == ""
        assert norm_phone("") == ""

    def test_numero_corto_se_descarta(self):
        assert norm_phone("123") == ""

    def test_transposicion_detecta_digitos_cambiados(self):
        assert "3052549031" in transposiciones("3052549013")

    def test_transposicion_no_incluye_el_original(self):
        assert "3052549013" not in transposiciones("3052549013")


class TestNombre:
    def test_apellido_primero_da_la_misma_clave(self):
        assert clave_nombre("López David") == clave_nombre("David López")

    def test_tildes_y_mayusculas_no_importan(self):
        assert clave_nombre("MARÍA RODRÍGUEZ") == clave_nombre("maria rodriguez")

    def test_identico_puntua_uno(self):
        assert sim_nombre("Ana Ruiz", "Ana", "Ruiz") == 1.0

    def test_segundo_apellido_no_hunde_el_score(self):
        assert sim_nombre("Ana Ruiz Gómez", "Ana", "Ruiz") >= 0.8

    def test_inicial_puntua_parcial(self):
        s = sim_nombre("A. Ruiz", "Ana", "Ruiz")
        assert 0.4 < s < 1.0

    def test_nombre_ajeno_puntua_bajo(self):
        assert sim_nombre("Carlos Pérez", "Ana", "Ruiz") < 0.3
