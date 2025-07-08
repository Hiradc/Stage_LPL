import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from SPARQLWrapper import SPARQLWrapper, JSON

def get_wikidata_id(label: str, lang="en") -> str:
    endpoint = SPARQLWrapper("https://query.wikidata.org/sparql")
    query = f"""
    SELECT ?item WHERE {{
      ?item rdfs:label "{label}"@{lang} .
    }} LIMIT 1
    """
    endpoint.setQuery(query)
    endpoint.setReturnFormat(JSON)
    results = endpoint.query().convert()
    bindings = results["results"]["bindings"]
    return bindings[0]["item"]["value"].split("/")[-1] if bindings else None

def get_semantic_paths(term1: str, term2: str, lang="en", max_results=None):
    id1 = get_wikidata_id(term1, lang)
    id2 = get_wikidata_id(term2, lang)

    if not id1 or not id2:
        raise ValueError("Un ou les deux termes n'ont pas pu être trouvés sur Wikidata.")

    print(f"🔎 Résolution des entités : '{term1}' → {id1}, '{term2}' → {id2}")

    endpoint = SPARQLWrapper("https://query.wikidata.org/sparql")
    limit_clause = f"LIMIT {max_results}" if max_results else ""

    query = f"""
    SELECT ?step1Label ?rel1Label ?step2Label ?rel2Label ?step3Label ?rel3Label ?step4Label ?rel4Label ?step5Label WHERE {{
      wd:{id1} ?p1 ?step1 .
      ?rel1 wikibase:directClaim ?p1 .
      ?step1 ?p2 ?step2 .
      ?rel2 wikibase:directClaim ?p2 .
      ?step2 ?p3 ?step3 .
      ?rel3 wikibase:directClaim ?p3 .
      ?step3 ?p4 ?step4 .
      ?rel4 wikibase:directClaim ?p4 .
      ?step4 ?p5 wd:{id2} .

      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "{lang}" . }}
    }}
    {limit_clause}
    """
    endpoint.setQuery(query)
    endpoint.setReturnFormat(JSON)
    results = endpoint.query().convert()

    chains = []
    for res in results["results"]["bindings"]:
        try:
            path = [
                term1,
                "→", res["rel1Label"]["value"],
                "→", res["step1Label"]["value"],
                "→", res["rel2Label"]["value"],
                "→", res["step2Label"]["value"],
                "→", res["rel3Label"]["value"],
                "→", res["step3Label"]["value"],
                "→", res["rel4Label"]["value"],
                "→", res["step4Label"]["value"],
                "→", term2
            ]
            chains.append(" ".join(path))
        except KeyError:
            continue

    return chains
    
if __name__ == "__main__":
    print("🌍 Recherche de chemin sémantique entre deux concepts via Wikidata")
    concept1 = input("📝 Entrez le premier concept : ")
    concept2 = input("📝 Entrez le second concept : ")

    use_limit = input("Souhaitez-vous fixer un nombre maximal de résultats ? (y/n) : ").strip().lower()
    max_results = int(input("🔢 Nombre maximal de résultats à retourner : ")) if use_limit == "y" else None

    try:
        chemins = get_semantic_paths(concept1, concept2, lang="en", max_results=max_results)
        if not chemins:
            print("❌ Aucun chemin trouvé.")
        else:
            print(f"\n🔗 {len(chemins)} chemin(s) trouvé(s) :")
            for chemin in chemins:
                print(chemin)
    except Exception as e:
        print("❗ Erreur :", e)