import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, make_pipeline, make_union

# Mensajes de ejemplo ya etiquetados. Para mejorar el clasificador basta con
# agregar filas a este archivo; el modelo se entrena solo al arrancar.
RUTA_EJEMPLOS = (
    Path(__file__).resolve().parent.parent / "datos" / "incidencias_entrenamiento.csv"
)

# Categoría de los mensajes que no reportan nada: saludos, "entrada", consultas.
SIN_INCIDENCIA = "Ninguna"

# Por debajo de esta confianza la clasificación queda marcada para revisión humana.
CONFIANZA_MINIMA = 0.6


@dataclass(frozen=True)
class Clasificacion:
    categoria: str  # 'Retardo', 'Ausencia', 'Permiso', 'General' o 'Ninguna'
    prioridad: str  # 'Alta', 'Media' o 'Baja'
    confianza: float  # de 0 a 1

    @property
    def es_incidencia(self) -> bool:
        return self.categoria != SIN_INCIDENCIA

    @property
    def ambigua(self) -> bool:
        return self.confianza < CONFIANZA_MINIMA


def leer_ejemplos() -> list[dict]:
    with open(RUTA_EJEMPLOS, encoding="utf-8", newline="") as archivo:
        return list(csv.DictReader(archivo))


def nuevo_modelo() -> Pipeline:
    # El texto se convierte en números con TF-IDF, sin acentos ni mayúsculas.
    # Los fragmentos de letras toleran faltas de ortografía ("boy a yegar");
    # las palabras y pares de palabras conservan el sentido ("no voy").
    opciones = {"strip_accents": "unicode", "lowercase": True, "sublinear_tf": True}
    letras = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), **opciones)
    palabras = TfidfVectorizer(
        analyzer="word", ngram_range=(1, 2), token_pattern=r"(?u)\b\w+\b", **opciones
    )
    return make_pipeline(
        make_union(letras, palabras),
        LogisticRegression(C=10, max_iter=2000, class_weight="balanced"),
    )


@lru_cache(maxsize=1)
def modelos() -> tuple[Pipeline, Pipeline]:
    # Se entrenan una sola vez, la primera vez que se clasifica un mensaje.
    ejemplos = leer_ejemplos()
    incidencias = [e for e in ejemplos if e["categoria"] != SIN_INCIDENCIA]

    de_categoria = nuevo_modelo().fit(
        [e["texto"] for e in ejemplos], [e["categoria"] for e in ejemplos]
    )
    de_prioridad = nuevo_modelo().fit(
        [e["texto"] for e in incidencias], [e["prioridad"] for e in incidencias]
    )
    return de_categoria, de_prioridad


def _predecir(modelo: Pipeline, texto: str) -> tuple[str, float]:
    probabilidades = modelo.predict_proba([texto])[0]
    mejor = probabilidades.argmax()
    return str(modelo.classes_[mejor]), float(probabilidades[mejor])


def clasificar(texto: str) -> Clasificacion:
    de_categoria, de_prioridad = modelos()
    categoria, confianza_categoria = _predecir(de_categoria, texto)
    prioridad, confianza_prioridad = _predecir(de_prioridad, texto)

    if categoria == SIN_INCIDENCIA:
        return Clasificacion(categoria, prioridad, confianza_categoria)

    # Basta con que una de las dos respuestas sea dudosa para pedir revisión.
    return Clasificacion(
        categoria, prioridad, min(confianza_categoria, confianza_prioridad)
    )


def evaluar(particiones: int = 5) -> None:
    # Validación cruzada: cada ejemplo se clasifica con un modelo que no lo vio.
    from sklearn.metrics import classification_report
    from sklearn.model_selection import StratifiedKFold, cross_val_predict

    ejemplos = leer_ejemplos()
    incidencias = [e for e in ejemplos if e["categoria"] != SIN_INCIDENCIA]
    corte = StratifiedKFold(particiones, shuffle=True, random_state=0)

    for titulo, datos, columna in (
        ("CATEGORÍA", ejemplos, "categoria"),
        ("PRIORIDAD", incidencias, "prioridad"),
    ):
        textos = [e["texto"] for e in datos]
        reales = [e[columna] for e in datos]
        probabilidades = cross_val_predict(
            nuevo_modelo(), textos, reales, cv=corte, method="predict_proba"
        )
        clases = sorted(set(reales))
        predichas = [clases[i] for i in probabilidades.argmax(axis=1)]
        seguras = probabilidades.max(axis=1) >= CONFIANZA_MINIMA
        aciertos = [
            real == predicha
            for real, predicha, segura in zip(reales, predichas, seguras)
            if segura
        ]

        print(f"\n{titulo} ({len(datos)} ejemplos, {particiones} particiones)")
        print(classification_report(reales, predichas, digits=3))
        print(
            f"Con confianza de {CONFIANZA_MINIMA} o más: "
            f"{seguras.mean():.0%} de los mensajes, "
            f"{sum(aciertos) / len(aciertos):.0%} de aciertos. "
            "El resto queda para revisión humana."
        )


if __name__ == "__main__":
    evaluar()
