# Simulator and study diagrams

These diagrams accompany the generated plots and explain the model mechanisms
that response curves alone cannot show.

## Simulator mechanism

```mermaid
flowchart LR
    A["Element-class percentages"] --> B["Generated class membership"]
    C["Selection-class percentages"] --> D["Class probability mass"]
    E["Concentration and rescaling"] --> F["Element transition probabilities"]
    G["Duration profiles"] --> H["Layer transition timing"]
    B --> I["Selected exact C3-C6 rules"]
    D --> F
    F --> J["Active six-layer state"]
    H --> J
    I --> K["Exact rule match"]
    J --> K
    K --> L["Unknown episodes"]
    L --> M["Rate, occupancy, duration, dispersion"]
```

## Exact-combination matching

```mermaid
flowchart TB
    S["Current state: one active element per layer"] --> R{"Any unknown-class element active?"}
    R -- "yes" --> X["No exact-combination match"]
    R -- "no" --> T{"Active rare set equals one selected rule?"}
    T -- "no" --> X
    T -- "yes" --> U{"Rule contains a rare triggering condition?"}
    U -- "yes" --> O["Open or continue C3-C6 episode"]
    U -- "no" --> X
```

Every selected rule contains the triggering-condition layer by construction.
Layers not named by the rule must be common; extra rare elements invalidate the
match.

## Conditional-transition mechanism

```mermaid
flowchart LR
    P["Parent-layer context"] --> Q{"Conditional selector matches?"}
    Q -- "no" --> B["Base target-layer vector"]
    Q -- "yes" --> M["Apply element or rarity multipliers"]
    M --> N["Renormalize target-layer vector"]
    B --> S["Sample next target element"]
    N --> S
    S --> E["Changed scenario exposure"]
```

## Taxonomy-to-risk pathway

```mermaid
flowchart LR
    A["Layer element count"] --> B["Integer class counts"]
    C["Class selection mass"] --> D["Mass per element"]
    B --> D
    D --> E["Mass of each selected rule"]
    F["Rule count and C-size"] --> E
    E --> G["Episode-entry opportunity"]
    H["Layer durations"] --> I["Transition frequency and persistence"]
    G --> J["Observed unknown episodes"]
    I --> J
```
