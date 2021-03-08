"""Geo Sampa Import/Export

Usage:
  geosampa.py import [--output=<import-output>] [--theme=<filter-theme>] [--sub-theme=<filter-sub-theme>] [--host=<geosampa-host>]
  geosampa.py export ckan [--input=<export-input>] [--site=<ckan-site>] [--public] [--api-key=<ckan-api-key>] [--organization=<ckan-org>]
  geosampa.py (-h | --help)
  geosampa.py --version

Options:
  -h --help                     Show this screen.
  --version                     Show version.
  --output=<import-output>      GeoSampa files will be downloaded to [default: ./].
  --theme=<filter-theme>        Filter GeoSampa Themes.
  --sub-theme=<filter-theme>    Filter GeoSampa Sub-themes.
  --host=<geosampa-host>        GeoSampa files will be downloaded to [default: http://geosampa.prefeitura.sp.gov.br].
  --site=<ckan-site>            Your ckan site. i.e.: https://dataurbe.appcivico.com/
  --api-key=<ckan-api-key>      Your CKAN API Key.
  --organization=<ckan-org>     The CKAN Organization the datasets will be created
  --public                      Create public datasets
"""
import json
import re

from docopt import docopt
import os
from os import path

from PyInquirer import prompt
from slugify import slugify
from tqdm import tqdm
from urllib.parse import urlencode, quote
import requests

from ckanapi import RemoteCKAN
from hashlib import sha1


def get_sub_folders(folder_name, host):
    response = requests.post(host + "/PaginasPublicas/_SBC.aspx/pesquisaSubPastas", json={
        "pNomePasta": folder_name
    })

    result = response.json()
    return [re.sub(r":[0-9]+", "", f) for f in result["d"].split("|") if f]


def get_files(folder_name, host):
    response = requests.post(host + "/PaginasPublicas/_SBC.aspx/pesquisaArquivos", json={
        "pNomePasta": folder_name
    })

    result = response.json()
    return [f for f in result["d"].split("|") if f]


def find_geosampa_files(geosampa_host):
    themes = get_sub_folders("TEMAS", geosampa_host)
    base_link_url = geosampa_host + "/PaginasPublicas/downloadArquivoOL.aspx"

    for theme in themes:

        sub_themes = get_sub_folders(theme, geosampa_host)
        for sub_theme in sub_themes:
            folder = f"{theme}//{sub_theme}//"
            layers = get_sub_folders(folder, geosampa_host)

            for layer in layers:
                folder = f"{theme}//{sub_theme}//{layer}"
                files = get_files(folder, geosampa_host)

                for file in files:

                    file_name = re.sub(r"\.[a-z]{3}", "", file)
                    file_path = f"{theme}\\\\{sub_theme}\\\\{layer}\\\\{file_name}"
                    try:
                        file_path = file_path.encode('latin-1')
                    except:
                        pass

                    yield {
                        'theme': theme,
                        'sub_theme': sub_theme,
                        'layer': layer,
                        'file': file,
                        "link": base_link_url + "?" + urlencode({
                            "orig": "DownloadCamadas",
                            "arqTipo": layer,
                            "arq": file_path
                        }, quote_via=quote)
                    }


def download_file(geosampa_file, output):
    parts = [
        geosampa_file['theme'],
        geosampa_file['sub_theme'],
        geosampa_file['layer'],
    ]

    filename = "-".join([re.sub(r'[^a-z1-9\_\-]', '', p.lower()) for p in parts]) + "-" + geosampa_file['file']

    local_filename = path.join(output, filename)
    if path.exists(local_filename):
        print(f"Skipping {local_filename}. Already exists")

    try:
        with requests.get(geosampa_file['link'], stream=True) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in tqdm(r.iter_content(chunk_size=8192), desc="Downloading " + filename):
                    f.write(chunk)
    except:
        if path.exists(local_filename):
            os.remove(local_filename)

    with open(local_filename + '.meta.json', 'w', encoding='latin-1') as m:
        json.dump(geosampa_file, fp=m, indent=4)


def import_from_geosampa(arguments):
    output = arguments['--output']
    output = output if path.isabs(output) else path.abspath(output)
    if not path.exists(output):
        raise Exception('The output path does not exists.')
    elif not path.isdir(output):
        raise Exception('The output path is not a directory.')

    geosampa_host = arguments['--host']
    filter_theme = arguments['--theme']
    filter_sub_theme = arguments['--sub-theme']

    for geosampa_file in find_geosampa_files(geosampa_host):
        if filter_theme and geosampa_file['theme'] != filter_theme:
            continue

        if filter_sub_theme and geosampa_file['sub_theme'] != filter_sub_theme:
            continue

        download_file(geosampa_file, output)


def find_package(ckan, name):
    response = ckan.call_action("package_search",
                                {"fq": f"name:{name}", "include_private": True, "include_drafts": True})
    if response["count"] > 0:
        return response["results"][0]
    else:
        return None


def create_or_update_package(ckan, data):
    pkg = find_package(ckan, data["name"])
    if not pkg:
        pkg = ckan.call_action("package_create", data)
    else:
        data["id"] = pkg["id"]
        pkg = ckan.call_action("package_patch", data)

    return pkg


def find_resource(ckan, resource_hash):
    response = ckan.call_action("resource_search", {"query": f"hash:{resource_hash}"})
    if response["count"] > 0:
        return response["results"][0]
    else:
        return None


def create_or_update_resource(ckan, data, fp):
    try:
        res = find_resource(ckan, data["hash"])
        if not res:
            res = ckan.call_action("resource_create", data, files={'upload': fp})
        else:
            data["id"] = res["id"]
            res = ckan.call_action("resource_patch", data, files={'upload': fp})

        return res
    except:
        return None


def export_file(ckan, original_file, file, org, public, packages_cache):
    theme_name = re.sub(r"[0-9]+_", "", file["theme"])
    sub_theme = file["sub_theme"]
    if theme_name == sub_theme:
        resource_title = f"[GeoSampa] {theme_name}"
    else:
        resource_title = f"[GeoSampa] {theme_name} - {sub_theme}"

    pkg_name = slugify(resource_title)
    if pkg_name not in packages_cache:
        packages_cache[pkg_name] = create_or_update_package(ckan, {
            "name": pkg_name,
            "title": resource_title,
            "notes": "Conjunto de dados extraido automaticamente de http://geosampa.prefeitura.sp.gov.br/",
            "owner_org": org["id"],
            "private": not public,
            "author": "GeoSampa",
            "author_email": "geosampa@prefeitura.sp.gov.br",
            "source": "http://geosampa.prefeitura.sp.gov.br/",
            "tags": [
                {"name": "geosampa"},
                {"name": theme_name},
                {"name": sub_theme}
            ]
        })

    create_or_update_resource(ckan, {
        "package_id": packages_cache[pkg_name]["id"],
        "url": file["link"],
        "name": file["file"],
        "format": file["layer"],
        "mimetype": "application/zip" if file["file"].endswith(".zip") else None,
        "cache_url": file["link"],
        "hash": sha1((pkg_name + file["file"]).encode("utf8")).hexdigest()
    }, open(original_file, 'rb'))


def export_to_ckan(arguments):
    input_dir = arguments['--input']
    input_dir = input_dir if path.isabs(input_dir) else path.abspath(input_dir)
    ckan_host = arguments['--site']
    organization = arguments['--organization']
    api_key = arguments['--api-key']
    public = arguments['--public']

    if not ckan_host:
        ckan_host = prompt({
            'type': 'input',
            'name': 'ckan_host',
            'message': 'Inform your CKAN API Site: '
        })['ckan_host']

    if not api_key:
        api_key = prompt({
            'type': 'input',
            'name': 'api_key',
            'message': 'Inform your CKAN API Key:'
        })['api_key']

    ckan = RemoteCKAN(ckan_host, apikey=api_key)
    organizations = ckan.call_action("organization_list", {"all_fields": True})

    if not organization:
        organization = prompt({
            'type': 'list',
            'name': 'organization',
            'message': 'Select the organization:',
            'choices': [o['name'] for o in organizations]
        })['organization']

    packages_cache = {}
    selected_org = next(filter(lambda o: o['name'] == organization, organizations))
    for meta_file in filter(lambda f: f.endswith("meta.json"), tqdm(os.listdir(input_dir))):

        original_file = meta_file.replace('.meta.json', '')
        original_file = path.join(input_dir, original_file)
        meta_file = path.join(input_dir, meta_file)

        if path.exists(original_file):

            with open(meta_file, 'r', encoding='latin-1') as mfp:
                meta_data = json.load(fp=mfp)

            export_file(ckan, original_file, meta_data, selected_org, public, packages_cache)

        else:
            print(f"{original_file} not found. Deleting meta the data file.")
            os.remove(meta_file)


def main():
    arguments = docopt(__doc__, version='1.0')

    if arguments['import']:
        import_from_geosampa(arguments)
    elif arguments['export'] and arguments['ckan']:
        export_to_ckan(arguments)
    else:
        print("Unknown command")


if __name__ == '__main__':
    main()
