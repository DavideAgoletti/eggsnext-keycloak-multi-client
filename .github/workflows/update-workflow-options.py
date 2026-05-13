#!/usr/bin/env python3
"""
Script per aggiornare automaticamente i dropdown del workflow
con le versioni e i client disponibili
"""

import json
import subprocess
import requests
import yaml
import sys
import re

def get_keycloak_versions(limit=20):
    """Recupera le versioni e filtra per mostrare solo le ultime di ogni release Minor"""
    try:
        # Aumentiamo il limite a 500 per raggiungere le versioni più vecchie (25, 24, ecc.)
        response = requests.get(
            'https://quay.io/api/v1/repository/keycloak/keycloak/tag?limit=500',
            timeout=10
        )
        response.raise_for_status()

        tags = response.json().get('tags', [])
        all_stable = []

        for tag in tags:
            name = tag.get('name', '')
            # Filtro base: solo versioni stabili X.Y.Z
            if re.match(r'^\d+\.\d+\.\d+$', name):
                if not any(x in name.lower() for x in ['alpha', 'beta', 'rc', 'dev', 'snapshot']):
                    all_stable.append(name)

        # Ordina dalla più recente
        all_stable.sort(key=lambda x: tuple(map(int, x.split('.'))), reverse=True)

        # Raggruppa per Major.Minor e tieni solo l'ultima patch
        latest_per_minor = {}
        for v in all_stable:
            major_minor = ".".join(v.split('.')[:2])
            if major_minor not in latest_per_minor:
                latest_per_minor[major_minor] = v

        filtered_versions = list(latest_per_minor.values())
        filtered_versions.sort(key=lambda x: tuple(map(int, x.split('.'))), reverse=True)

        print(f"✅ Filtrate {len(filtered_versions)} versioni uniche")
        return filtered_versions[:limit]

    except Exception as e:
        print(f"❌ Errore: {e}", file=sys.stderr)
        return []
def get_available_clienti():
    """Recupera i clienti disponibili dalla struttura clienti/"""
    try:
        result = subprocess.run(
            ["find", "clienti", "-maxdepth", "1", "-type", "d"],
            capture_output=True,
            text=True
        )

        clienti = [
            d.split('/')[-1] for d in result.stdout.strip().split('\n')
            if d and d != 'clienti' and d.strip()
        ]

        print(f"✅ Trovati {len(clienti)} clienti:")
        for c in clienti:
            print(f"   - {c}")
        return sorted(clienti)

    except Exception as e:
        print(f"❌ Errore nel recuperare clienti: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return []

def update_workflow(versions, clienti):
    """Aggiorna il file workflow con le nuove opzioni"""
    workflow_path = '.github/workflows/build-image.yml'

    try:
        # Leggi il file YAML
        with open(workflow_path, 'r') as f:
            content = f.read()

        # Parse YAML
        workflow = yaml.safe_load(content)

        # ✅ SOLUZIONE: La chiave 'on:' in YAML diventa True in PyYAML
        trigger_key = True

        if trigger_key not in workflow:
            print(f"❌ Chiave 'on' (True) non trovata nel workflow!", file=sys.stderr)
            print(f"Chiavi disponibili: {list(workflow.keys())}", file=sys.stderr)
            return False

        # Verifica che workflow_dispatch esista
        if 'workflow_dispatch' not in workflow[trigger_key]:
            print("❌ workflow_dispatch non trovato nel trigger 'on'", file=sys.stderr)
            return False

        # Aggiorna gli input
        clienti_options = ['all'] + clienti
        version_options = versions

        # Accedi ai trigger e aggiorna
        workflow[trigger_key]['workflow_dispatch']['inputs']['client']['options'] = clienti_options
        workflow[trigger_key]['workflow_dispatch']['inputs']['keycloak_version']['options'] = version_options

        # Scrivi il file aggiornato con configurazione YAML pulita
        with open(workflow_path, 'w') as f:
            yaml.dump(
                workflow,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True
            )

        # Leggi il file e rimpiazza True con 'on' nella prima linea di trigger
        with open(workflow_path, 'r') as f:
            content = f.read()

        # Rimpiazza "True:" con "on:" nelle sezioni appropriate
        lines = content.split('\n')
        fixed_lines = []
        for i, line in enumerate(lines):
            if i < 10 and line.strip() == 'True:':  # Cerca True nei primi 10 righe (sezione trigger)
                fixed_lines.append('on:')
            else:
                fixed_lines.append(line)

        with open(workflow_path, 'w') as f:
            f.write('\n'.join(fixed_lines))

        print(f"\n✅ Workflow aggiornato!")
        print(f"   Clienti ({len(clienti_options)}): {', '.join(clienti_options)}")
        print(f"   Versioni ({len(version_options)}): {', '.join(version_options[:5])}...")

        return True

    except Exception as e:
        print(f"❌ Errore nell'aggiornamento: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("🔄 Aggiornamento opzioni workflow...")
    print()

    versions = get_keycloak_versions(20)
    clienti = get_available_clienti()

    print()
    if versions and clienti:
        if update_workflow(versions, clienti):
            print("\n🎉 Aggiornamento completato con successo!")
            sys.exit(0)

    print("\n❌ Impossibile recuperare versioni o clienti")
    sys.exit(1)