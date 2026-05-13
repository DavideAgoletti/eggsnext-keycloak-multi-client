#!/usr/bin/env python3
import requests
import yaml
import sys
import re
import subprocess

def get_keycloak_versions():
    """Recupera le versioni Major (dalla 18 alla più recente) paginando l'API"""
    latest_per_major = {}
    page = 1
    has_additional = True

    print("🔍 Ricerca versioni Major (dalla 26 alla 18)...")

    try:
        # Continua a cercare finché ci sono pagine o finché non abbiamo coperto il range
        while has_additional and page < 10:  # Limite di sicurezza a 10 pagine
            url = f'https://quay.io/api/v1/repository/keycloak/keycloak/tag/?limit=100&page={page}'
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()

            tags = data.get('tags', [])
            if not tags:
                break

            for tag in tags:
                name = tag.get('name', '')
                # Filtro X.Y.Z stabile
                if re.match(r'^\d+\.\d+\.\d+$', name):
                    if not any(x in name.lower() for x in ['alpha', 'beta', 'rc', 'dev', 'snapshot']):
                        major = int(name.split('.')[0])

                        # Se è una major che ci interessa (>= 18) e non l'abbiamo ancora salvata
                        if major >= 18:
                            # Poiché l'API restituisce i tag dal più recente,
                            # la prima che troviamo per ogni Major è la patch più alta
                            if major not in latest_per_major:
                                latest_per_major[major] = name
                                print(f"   ⭐ Trovata Major {major}: {name}")

            has_additional = data.get('has_additional', False)
            page += 1

        # Ordiniamo i risultati (26, 25, 24...)
        sorted_majors = sorted(latest_per_major.keys(), reverse=True)
        filtered_versions = [latest_per_major[m] for m in sorted_majors]

        return filtered_versions

    except Exception as e:
        print(f"❌ Errore API: {e}", file=sys.stderr)
        return []

def get_available_clienti():
    """Rileva i clienti basandosi sulle cartelle presenti"""
    # Cerchiamo sia 'clients' che 'clienti' per sicurezza
    for folder in ['clients', 'clienti']:
        try:
            result = subprocess.run(
                ["ls", "-d", f"{folder}/*/"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return sorted([d.split('/')[-2] for d in result.stdout.strip().split('\n') if d])
        except:
            continue
    return ["errevi", "errezeta", "papalini", "poma"]

def update_workflow(versions, clienti):
    """Aggiorna il file build-image.yml"""
    workflow_path = '.github/workflows/build-image.yml'
    try:
        with open(workflow_path, 'r') as f:
            workflow = yaml.safe_load(f)

        # In PyYAML 'on:' viene letto come True
        trigger = True
        if trigger in workflow:
            inputs = workflow[trigger]['workflow_dispatch']['inputs']
            inputs['client']['options'] = ['all'] + clienti
            inputs['keycloak_version']['options'] = versions

            with open(workflow_path, 'w') as f:
                yaml.dump(workflow, f, default_flow_style=False, sort_keys=False)

            # Ripristina 'on:' al posto di 'True:'
            with open(workflow_path, 'r') as f:
                content = f.read()
            with open(workflow_path, 'w') as f:
                f.write(content.replace('True:', 'on:'))
            return True
    except Exception as e:
        print(f"❌ Errore aggiornamento file: {e}")
        return False

if __name__ == '__main__':
    versions = get_keycloak_versions()
    clienti = get_available_clienti()

    if versions:
        if update_workflow(versions, clienti):
            print(f"\n🎉 Successo! Inserite {len(versions)} versioni nel dropdown.")
        else:
            sys.exit(1)
    else:
        print("❌ Nessuna versione trovata.")
        sys.exit(1)