"""
lab.config.settings._load_env_file() solo rellena una variable si todavia
NO esta en os.environ, y ese relleno pasa la PRIMERA vez que se importa
lab.config.settings en el proceso. Si esa primera importacion ocurre DENTRO
de un test (ej. via CloudflareFluxProvider.__init__ -> "import lab.config.settings"),
despues de que el test ya hizo monkeypatch.delenv sobre una credencial,
_load_env_file() la repuebla desde el lab/config/.env real -- deshaciendo el
delenv sin que el test se entere. Importar settings aca, una sola vez, antes
de que corra cualquier test, hace que ese relleno pase en un momento
predecible y que los monkeypatch.delenv posteriores sean confiables.
"""

import lab.config.settings  # noqa: F401
