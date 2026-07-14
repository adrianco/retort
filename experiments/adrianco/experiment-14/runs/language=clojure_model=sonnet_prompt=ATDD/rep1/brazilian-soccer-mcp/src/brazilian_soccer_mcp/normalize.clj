(ns brazilian-soccer-mcp.normalize
  "Team name normalization utilities for consistent matching across datasets.")

;; Map of canonical team names and all their known aliases
(def ^:private canonical-names
  {"Flamengo"    #{"Flamengo" "Flamengo-RJ" "CR Flamengo" "Clube de Regatas do Flamengo"}
   "Fluminense"  #{"Fluminense" "Fluminense-RJ" "Fluminense FC"}
   "Vasco"       #{"Vasco" "Vasco-RJ" "Vasco da Gama" "CR Vasco da Gama"}
   "Botafogo"    #{"Botafogo" "Botafogo-RJ" "Botafogo FR"}
   "Palmeiras"   #{"Palmeiras" "Palmeiras-SP" "SE Palmeiras"}
   "Corinthians" #{"Corinthians" "Corinthians-SP" "Sport Club Corinthians Paulista" "SC Corinthians Paulista"}
   "Santos"      #{"Santos" "Santos-SP" "Santos FC"}
   "São Paulo"   #{"São Paulo" "Sao Paulo" "São Paulo-SP" "Sao Paulo-SP" "SPFC" "São Paulo FC" "Sao Paulo FC"}
   "Grêmio"      #{"Grêmio" "Gremio" "Grêmio-RS" "Gremio-RS" "Grêmio FBPA"}
   "Internacional" #{"Internacional" "Internacional-RS" "SC Internacional" "Inter"}
   "Atlético-MG" #{"Atlético-MG" "Atletico-MG" "Atletico MG" "Atlético Mineiro" "Atletico Mineiro" "Club Atletico Mineiro"}
   "Cruzeiro"    #{"Cruzeiro" "Cruzeiro-MG" "Cruzeiro EC"}
   "Bahia"       #{"Bahia" "Bahia-BA" "EC Bahia"}
   "Fortaleza"   #{"Fortaleza" "Fortaleza-CE" "Fortaleza EC"}
   "Ceará"       #{"Ceará" "Ceara" "Ceará-CE" "Ceara-CE" "Ceará SC"}
   "Sport"       #{"Sport" "Sport-PE" "Sport Club do Recife"}
   "Vitória"     #{"Vitória" "Vitoria" "Vitória-BA" "Vitoria-BA" "EC Vitória"}
   "Goiás"       #{"Goiás" "Goias" "Goiás-GO" "Goias-GO" "Goiás EC"}
   "Athletico-PR" #{"Athletico-PR" "Atletico-PR" "Athletico Paranaense" "Atletico Paranaense" "CAP" "Athletico"}
   "Coritiba"    #{"Coritiba" "Coritiba-PR" "Coritiba FC"}
   "Avaí"        #{"Avaí" "Avai" "Avaí-SC" "Avai-SC" "Avaí FC"}
   "Chapecoense" #{"Chapecoense" "Chapecoense-SC" "Associação Chapecoense de Futebol"}
   "Bragantino"  #{"Bragantino" "Red Bull Bragantino" "RB Bragantino" "Bragantino-SP"}
   "América-MG"  #{"América-MG" "America-MG" "América Mineiro" "America Mineiro"}
   "Cuiabá"      #{"Cuiabá" "Cuiaba" "Cuiabá-MT" "Cuiaba-MT"}
   "Juventude"   #{"Juventude" "Juventude-RS" "EC Juventude"}
   "Guarani"     #{"Guarani" "Guarani-SP" "Guarani FC"}
   "Ponte Preta" #{"Ponte Preta" "Ponte Preta-SP" "AA Ponte Preta"}
   "Portuguesa"  #{"Portuguesa" "Portuguesa-SP" "Portuguesa Desportos"}
   "Figueirense" #{"Figueirense" "Figueirense-SC" "Figueirense FC"}})

;; Reverse index: alias -> canonical
(def ^:private alias->canonical
  (into {}
        (for [[canonical aliases] canonical-names
              alias aliases]
          [(clojure.string/lower-case alias) canonical])))

(defn canonicalize
  "Return the canonical team name for any known alias, or the original if unknown."
  [team-name]
  (when team-name
    (let [lower (clojure.string/lower-case (clojure.string/trim team-name))]
      (or (alias->canonical lower)
          ;; strip state suffix and try again
          (let [stripped (clojure.string/replace lower #"-[a-z]{2}$" "")]
            (alias->canonical stripped))
          team-name))))

(defn team-matches?
  "True if the given name matches the query string (canonical or partial)."
  [query team-name]
  (when (and query team-name)
    (let [q-canon (canonicalize query)
          t-canon (canonicalize team-name)
          q-lower (clojure.string/lower-case (clojure.string/trim query))]
      (or (= (clojure.string/lower-case t-canon) (clojure.string/lower-case q-canon))
          (clojure.string/includes? (clojure.string/lower-case team-name) q-lower)
          (clojure.string/includes? (clojure.string/lower-case t-canon)
                                    (clojure.string/lower-case q-canon))))))
