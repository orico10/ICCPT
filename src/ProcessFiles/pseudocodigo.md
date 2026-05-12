# Método: updateSocialClusterParams

- **For demand multipliers:**
  - `new_elec_mult = (1 + DemMult["Electricity"]) ** yearDiff`
  - `new_cook_mult = (1 + DemMult["Cooking"]) ** yearDiff`
  - `new_heat_mult = (1 + DemMult["Heating"]) ** yearDiff`
  - → `params["EDemandMult"]` is updated accordingly.

- **Elasticity:**
  - `new_elast = (1 + dem_elast) ** yearDiff * baseElastDemand`
  - *Note:* `baseElastDemand` is stored in `params["EDemandElast"]`.

- **Other parameters:**
  - `Population = (1 + PopulGrowth) ** yearDiff`
  - `WillPay = baseWillPay * (1 + EconGrowth) ** yearDiff`
  - `InvestCap = baseInvestCap * (1 + EconGrowth) ** yearDiff`
  - `ChangeFact = min(baseChangeFact * (1 + ElastChange) ** yearDiff, 1.0)`
  - `BetterFact = baseBetterFact * (1 + ElastChange) ** yearDiff`
  - `WorseFact = baseWorseFact * (1 + ElastChange) ** yearDiff`
  - `SocialWeight = min(baseSocialWeight * (1 + SocWeight) ** yearDiff, 1.0)`

- **Social balance:**
  - *For each key* (`"Health"`, `"TimeGender"`, `"Emissions"`):
    - `new_value = base_value * (1 + SocialParams[key]) ** yearDiff`
  - `new_deforestation = max(1 - (new_health + new_timeGender + new_emissions), 0.0)`
  - *Then normalize the values so their sum is 1.*

---

- **Output:**
  - The updated parameters are stored back in:
    ```python
    self.demand_area.data["aggregated_clusters"][area_type]["params"]
    ```

## 🔧 **Método: calculate_reference_social_cost**

- **Propósito:**
  - Calcular el costo social de referencia para cada área (rural y urbana), basándose en la adopción inicial de cada tecnología y sus atributos sociales.

- **Parámetros de entrada:**
  - `self.technologies`: Lista de tecnologías con los siguientes atributos: `Technologies_id`, `Tech_name`, `Health`, `FuelTimeGen`, `ApplianceTimeGen`, `Emissions`, `Deforestation`.
  - `self.demand_area`: Objeto que contiene los datos de adopción inicial (`initial_adoptions`) para cada área (`rural`, `urban`).

- **Parámetros de salida:**
  - `self.ref_social_cost`: Diccionario con el costo social de referencia para cada área, estructurado de la siguiente forma:
    ```python
    {
        "rural": {"health": valor, "time_gen": valor, "emissions": valor, "deforestation": valor},
        "urban": {"health": valor, "time_gen": valor, "emissions": valor, "deforestation": valor}
    }
    ```

- **Cálculos:**
  1. Inicializar los valores totales en cero para cada componente social.
  2. Recorrer cada tecnología y multiplicar el valor de cada componente social por la adopción inicial correspondiente:
     ```python
     total_health += adoption * tech.Health
     total_time_gen += adoption * (tech.FuelTimeGen + tech.ApplianceTimeGen)
     total_emissions += adoption * tech.Emissions
     total_deforestation += adoption * tech.Deforestation
     ```
  3. Asignar los valores calculados a `self.ref_social_cost`, asegurando que ningún valor sea cero (mínimo 0.01).

- **¿Por qué se calcula?:**
  - Estos valores sirven como base para normalizar los costos sociales relativos de cada tecnología, permitiendo comparaciones proporcionales entre ellas.

---

## 🔧 **Método: assign_rel_social_cost**

- **Propósito:**
  - Calcular el costo social relativo para cada tecnología en áreas rurales y urbanas, ponderando factores de salud, tiempo, emisiones y deforestación.

- **Parámetros de entrada:**
  - `self.technologies`: Lista de tecnologías con atributos sociales.
  - `self.ref_social_cost`: Diccionario con los costos sociales de referencia previamente calculados.
  - `self.demand_area.data["aggregated_clusters"][area_type]["params"]["SocialBal"]`: Diccionario con los pesos sociales para cada componente (salud, tiempo, emisiones y deforestación).

- **Parámetros de salida:**
  - `self.rel_social_cost`: Diccionario con el costo social relativo para cada tecnología y área:
    ```python
    {
        "rural": {tech_id: weighted_cost, ...},
        "urban": {tech_id: weighted_cost, ...}
    }
    ```

- **Cálculos:**
  1. Normalizar cada componente social respecto a su valor de referencia:
     ```python
     relative_health = tech.Health / self.ref_social_cost[area_type]["health"]
     relative_time_gen = (tech.FuelTimeGen + tech.ApplianceTimeGen) / self.ref_social_cost[area_type]["time_gen"]
     relative_emissions = tech.Emissions / self.ref_social_cost[area_type]["emissions"]
     relative_deforestation = tech.Deforestation / self.ref_social_cost[area_type]["deforestation"]
     ```
  2. **Calcular el costo social ponderado:**
     ```python
     weighted_cost = (
         relative_health * social_weights.get("Health", 0.0) +
         relative_time_gen * social_weights.get("TimeGender", 0.0) +
         relative_emissions * social_weights.get("Emissions", 0.0) +
         relative_deforestation * social_weights.get("deforestation", 0.0)
     )
     ```
  3. Guardar el valor calculado en `self.rel_social_cost`.

- **¿Por qué se calcula?:**
  - El costo social relativo es crucial para evaluar el impacto de cada tecnología en el contexto social del área, facilitando comparaciones para decisiones de adopción más informadas.

# 📚 **Análisis detallado de métodos C++ en `CDemandAreaIncremental` (Pseudocódigo con entradas, salidas y propósito de cada cálculo)**

---

## 🔧 **Método: AssignRelSocialCost**
- **Propósito:** Calcular el costo social relativo para cada tecnología en áreas rurales y urbanas, ponderando factores de salud, tiempo, emisiones y deforestación.

- **Parámetros de entrada:**
  - `technologies`: Lista de tecnologías.
  - `CSocCluPar socParams`: Parámetros sociales.
  - `bool isUrban`: Indicador de área urbana o rural.

- **Parámetros de salida:**
  - `m_mibd_rel_socialCost[techID][isUrban]`: Costo social relativo calculado.

- **Cálculos:**
  1. Normalizar cada componente social:
     - `relativeHealthCost = health / totalHealth`
     - `relativeTimeGenCost = timeGen / totalTimeGen`
     - `relativeEmissionsCost = emissions / totalEmissions`
     - `relativeDeforestationCost = deforestation / totalDeforestation`
  2. **Calcular el costo social ponderado:**
     ```
     weightedCost = (relativeHealthCost * HealthWeight) +
                    (relativeTimeGenCost * TimeGenderWeight) +
                    (relativeEmissionsCost * EmissionsWeight) +
                    (relativeDeforestationCost * DeforestationWeight)
     ```

- **¿Por qué se calcula?:** Para evaluar el impacto social total de cada tecnología según su contribución relativa a diferentes factores sociales.

---

## 🔧 **Método: CalculateModifiedFAPrice**
- **Propósito:** Calcular precios modificados de combustibles y electrodomésticos considerando planes de precios y multiplicadores locales.

- **Parámetros de entrada:**
  - `technologies`: Lista de tecnologías.
  - `CPL0Plan* m_plo0`: Plan de precios.

- **Parámetros de salida:**
  - `m_mibd_fPrice_plan[fuelID][isUrban]`: Precio de combustible.
  - `m_mibd_aPrice_plan[applID][isUrban]`: Precio de electrodomésticos.

- **Cálculos:**
  ```
  localFuelPrice = fuelPrice * multiplier
  fuelPlanPrice = localFuelPrice * (fDepPrice > 0 ? fDepPrice : fPrice)
  appliancePlanPrice = applPrice * aPrice
  ```

- **¿Por qué se calcula?:** Para obtener precios ajustados al contexto local y tecnológico, que luego se usan para calcular costos totales de uso.

---

## 🔧 **Método: CalculatePriceTime**
- **Propósito:** Determinar el costo del tiempo de uso de cada tecnología.

- **Parámetros de entrada:**
  - `technologies`: Lista de tecnologías.
  - `double investCap`: Capacidad de inversión.
  - `double willPay`: Disposición a pagar.

- **Parámetros de salida:**
  - `m_mibd_priceTime[techID][isUrban]`: Precio del tiempo modificado.

- **Cálculo:**
  ```
  timePriceModified = investCap * willPay * multiplier
  ```

- **¿Por qué se calcula?:** Refleja el costo temporal asociado al uso de la tecnología, clave para el análisis de adopción.

---

## 🔧 **Método: CalculateRefCookingPrice**
- **Propósito:** Calcular el precio de cocción de referencia para cada tecnología.

- **Parámetros de entrada:**
  - `technologies`: Lista de tecnologías.
  - Precios calculados previamente (`fPrice`, `aPrice`, `timePrice`).

- **Parámetros de salida:**
  - `m_totalRefCookingPrice[isUrban]`: Precio de referencia final.

- **Cálculos:**
  ```
  absCookingPrice = fPrice + aPrice + timePrice
  mediaTP = (totalRefCookingPrice + willPay) / 2
  finalPrice = max(mediaTP, 0.01)
  ```

- **¿Por qué se calcula?:** Para establecer un valor base de costos relacionados con la cocción que se utilizará en cálculos relativos posteriores.

---

## 🔧 **Método: AssingRelCookingPrice**
- **Propósito:** Asignar el precio relativo de cocción para cada tecnología.

- **Parámetros de entrada:**
  - `m_mibd_abs_cookingPrice`: Precio absoluto de cocción.

- **Parámetros de salida:**
  - `m_mibd_rel_cookingPrice[techID][isUrban]`: Precio relativo calculado.

- **Cálculo:**
  ```
  relCookingPrice = absCookingPrice / m_totalRefCookingPrice[isUrban]
  ```

- **¿Por qué se calcula?:** Para comparar el costo de cocción relativo a un estándar común en el área.

---

## 🔧 **Método: CalculateProjectionWeights**
- **Propósito:** Calcular los pesos de proyección para priorizar tecnologías.

- **Parámetros de entrada:**
  - `relSocialCost`: Costo social relativo.
  - `relCookingPrice`: Precio relativo de cocción.
  - Factores sociales y económicos (`betterFactor`, `worseFactor`).

- **Parámetros de salida:**
  - `m_mibd_projectionWeights[techID][isUrban]`: Pesos de proyección calculados.

- **Cálculos:**
  ```
  socEconRep = socialWeight * relSocialCost + (1 - socialWeight) * relCookingPrice
  normalized = socEconRep <= 1 ? betterFactor * (1 / socEconRep - 1) : 1 + worseFactor * (socEconRep - 1)
  ```

- **¿Por qué se calcula?:** Para ponderar tecnologías basándose en criterios sociales y económicos ajustados a cada área.

---

## 🔧 **Método: ApplyPenaltiesAndNormalization**
- **Propósito:** Ajustar y normalizar tecnologías candidatas aplicando penalizaciones.

- **Parámetros de entrada:**
  - `appliancePrice`, `investCap`, `normalizedValue`, `availDeployYears`.

- **Parámetros de salida:**
  - `m_mibd_initialCandidate[techID][isUrban]`: Candidato inicial ajustado.

- **Cálculos:**
  ```
  reducedFactor = min(1.0, 0.5 * sqrt(investCap / appliancePrice))
  incrementalValue = (10 * initAdopt + normalizedValue * availDeployYears) / (10 + availDeployYears)
  ```

- **¿Por qué se calcula?:** Para reflejar la viabilidad de adopción de tecnologías considerando factores económicos.

---

## 🔧 **Método: CalculatePotentialAdoption**
- **Propósito:** Calcular la adopción potencial máxima para cada tecnología.

- **Parámetros de entrada:**
  - `technologies`, `deployPlan`, `initialCandidate`.

- **Parámetros de salida:**
  - `m_mibd_potentialAdoption[techID][isUrban]`: Adopción potencial final.

- **Cálculos clave:**
  ```
  reducedAppliance = min(maxAvail, initial)
  reducedFuel = min(reducedAppliance, reducedAppliance * fuelAvail / totalReducedAppliance)
  excess = initial - reducedFuel
  ```
  - **Iteraciones** hasta que `totalExcess == 0` o `totalCandidates == 0`.

- **¿Por qué se calcula?:** Para obtener la adopción realista que maximiza la capacidad disponible sin superar los límites tecnológicos o económicos.

---

📄 **Este análisis ahora incluye:**
- ✅ Parámetros de entrada y salida.
- ✅ Propósito detallado de cada cálculo.
- ✅ Explicación de por qué se realiza cada proceso.
