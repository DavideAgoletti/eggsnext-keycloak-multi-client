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

def get_keycloak_versions(limit=20):
    """Recupera le versioni disponibili da Quay.io"""
    try:
        response = requests.get(
            'https://quay.io/api/v1/repository/keycloak/keycloak/tag',
            timeout=10
        )
        response.raise_for_status()

        tags = response.json().get('tags', [])

        # Filtra solo le versioni (X.Y.Z)
        versions = [
            tag['name'] for tag in tags
            if tag['name'] and
               tag['name'][0].isdigit() and
               tag['name'].count('.') == 2
        ]

        # Ordina in discendente e prendi limite
        versions = sorted(versions, key=lambda x: tuple(map(int, x.split('.'))), reverse=True)
        return versions[:limit]

    except Exception as e:
        print(f"❌ Errore nel recuperare versioni: {e}", file=sys.stderr)
        return []

def get_available_clients():
    """Recupera i client disponibili dalla struttura"""
    try:
        result = subprocess.run(
            ["find", "clients", "-maxdepth", "1", "-type", "d"],
            capture_output=True,
            text=True
        )

        clients = [
            d.split('/')[-1] for d in result.stdout.strip().split('\n')
            if d and d != 'clients'
        ]

        return sorted(clients)

    except Exception as e:
        print(f"❌ Errore nel recuperare client: {e}", file=sys.stderr)
        return []

def update_workflow(versions, clients):
    """Aggiorna il file workflow con le nuove opzioni"""
    workflow_path = '.github/workflows/build-image.yml'

    try:
        # Leggi il file YAML
        with open(workflow_path, 'r') as f:
            workflow = yaml.safe_load(f)

        # Aggiorna gli input
        client_options = ['all'] + clients
        version_options = versions

        workflow['on']['workflow_dispatch']['inputs']['client']['options'] = client_options
        workflow['on']['workflow_dispatch']['inputs']['keycloak_version']['options'] = version_options

        # Scrivi il file aggiornato
        with open(workflow_path, 'w') as f:
            yaml.dump(workflow, f, default_flow_style=False, sort_keys=False)

        print(f"✅ Workflow aggiornato!")
        print(f"   Client: {', '.join(client_options)}")
        print(f"   Versioni: {', '.join(version_options[:5])}...")

        return True

    except Exception as e:
        print(f"❌ Errore nell'aggiornamento: {e}", file=sys.stderr)
        return False

if __name__ == '__main__':
    print("🔄 Aggiornamento opzioni workflow...")

    versions = get_keycloak_versions(20)
    clients = get_available_clients()

    if versions and clients:
        update_workflow(versions, clients)
    else:
        print("❌ Impossibile recuperare versioni o client")
        sys.exit(1)