# Axiomas del Ente Fractal — El UNO y el Tecelado Social

Documento formal del núcleo matemático de la topología social. Define el
ente fractal `u` (persona, grupo, clase o sociedad — el mismo objeto formal),
su identidad, su operatividad y su tejido de relaciones.

## 1. El UNO (definición)

Un ente fractal `u` es una **unidad** con dos capas:

```
u = ( identidad, estado )
identidad:  I(u) = e^{2πi} = 1      → invariante, el "volver a 1"
estado:     s(u,t) = (M_m, M_l, M_s, θ_m, θ_l, θ_s)   → cambia con el tiempo
unidad:     la trayectoria t ↦ s(u,t) es conexa → nunca se parte
```

El ente es una **tromba**: una hélice sobre `ℝ × T³` (el cubrimiento universal
del toro). El toro T³ = S¹×S¹×S¹ es la versión con memoria cerrada (tiempo
periódico); la tromba abre el tiempo (memoria acumulada) y la órbita ya no
cierra: `θ(t) = ω·t`.

```
e^{2πi}        →  un círculo de direcciones (compacto, infinito contenido)
×3             →  3 canales privilegiados: M (cuantificar), L (valorar), S (mover)
3×3 = 9        →  la grilla: acoplamientos = 9 nodos sociológicos
9×3 = 27       →  tercer orden = estado completo (vector 27D)
```

## 2. Los axiomas

| # | Axioma | Contenido |
|---|--------|-----------|
| U | Unidad | `I(u) = e^{2πi} = 1`. La identidad es invariante; el cambio vive solo en el estado. |
| T | Tromba | La trayectoria `t ↦ s(u,t)` es conexa en `ℝ × T³`. "No dejar de ser unidad" = la línea de mundo no se corta. |
| C | Clausura | La fase de cada canal es periódica: `θ_k(t+T) ≡ θ_k(t) mod 2π`. Cada rotación completa devuelve a la misma identidad; lo que avanza es la memoria. |
| S | Escala | `u` es el mismo objeto formal a toda escala (persona = grupo = clase = sociedad). El esqueleto 3→9→27 es invariante. |
| F | Falsabilidad | Todo estado `s(u,t)` es falsificable: el contenido `M` es no-real → se codifica como `e^{-2πiM}`. Para `M` entero colapsa a la identidad. |
| O | Operatividad | `x ↦ -1/x` (inversa negativa, involución): `u_op = e^{2πi/M}`. El ente solo computa con lo operativo. |
| D | Densidad | El tecelado se concentra alrededor de la fase dominante `θ*` (el núcleo). La dominancia es una densidad, no una fuerza. |

## 3. Semántica operativa (valoración → rayo → vértice)

Toda lógica `k ∈ {M, L, S}` valora todo nodo `Nⱼ` con un escalar `v ∈ [0,10]`
(0 = pésimo, 10 = buenísimo). El mapeo:

```
θ_{kj} = 360° / v_{kj}            ángulo (frecuencia)
p_{kj} = e^{i·θ_{kj}} ∈ S¹        vértice de contacto sobre el cuerpo unitario
```

- El **rayo** de la lógica parte del plano imaginario (falsificable).
- El **vértice** `p_{kj}` es donde la lógica se topa con la realidad — sobre el
  círculo de radio 1, la identidad misma (`u = 1`).
- El **tecelado** `T = {p_{kj}}` son los 27 vértices (`lógica × nodo`), el
  tejido de todos los juicios sobre el cuerpo.

## 4. El núcleo y el arrastre

```
k* = argmax(M_k)                  canal dominante
θ* = θ_{k*} = 360°/M_{k*}         fase dominante (el núcleo del ente)
R  = |Σ e^{i(φ_j − θ*)} / 27|     concentración circular (R → 1 = dominancia)
D(ε) = #(vértices a < ε de θ*) / 27   densidad del corte en la ventana ε
```

El arrastre es el **potencial del pozo**: el vértice efectivo se desplaza hacia
el núcleo según la densidad del corte y su desalineación:

```
p* = p + λ·R·f(Δθ)·(núcleo − p)      f(Δθ) = min(Δθ/π, 1)
```

**Predicción:** nodo deficiente + lógica dominante ⇒ el vértice del nodo se
agrupa en la cuenca del núcleo (el nodo se "socializa" y deja de responder a
su propia lógica).

## 5. El tecelado bajo arrastre

Los 27 vértices *efectivos* `p*` son lo que se mide (matriz de distancias δ).
La grilla 3×3 es la matriz etiquetada de los vértices de contacto; el tecelado
es su imagen sobre el cuerpo unitario.

## 6. Computabilidad (por qué el infinito no bloquea)

- **Compacidad:** el espacio operativo es `T³`, compacto; basta un ε-recubrimiento finito.
- **Suficiencia:** los invariantes (fases, ángulos relativos, giros) sobreviven a la falsabilidad; el contenido no.
- **Secuencialidad:** el eje abierto (memoria) es `ℝ`, pero la transición es
  Markoviana en el corte: horizonte infinito, costo finito por paso.
- **Clausura operativa:** `e^{-2πiM} = 1` para M entero — el contenido
  falsificable no distingue; la estructura emerge solo en el modo operativo `e^{2πi/M}`.

## 7. Implementación

- `src/topologia/math/unity.py` — núcleo puro: axiomas U, F, O, D.
- `src/topologia/math/coherence.py` — `evaluar_ente_fractal` (axioma S).
- `src/topologia/models/schemas.py` — `EnteFractal` (el UNO como entidad).
- `tests/test_unity.py` — 24 tests del núcleo.
